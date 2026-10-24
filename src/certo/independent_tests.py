"""Independent tests: written before the build, from the task text and the
project as it was then, run on the result after Certo's verdict, reported
next to it (DECISIONS.md, Phase 1.5).

The *test writer* is a separate, short conversation with only the file
editor, in a scratch folder outside the project. It sees the task text and
a read-only copy of the project before the build (`project_before/`; empty for a
new project), never the builder's work, so it can't copy the builder's
mistakes. It writes tests into `new_tests/` only for what the task and the
existing code state, or a `NO_TESTS.txt` saying why it wrote none (nothing
named to call, or no language). The folder stays outside the project
during the build, so the builder can't read, run or edit the tests;
afterwards `bench_tasks.run_test_folder` copies them in, runs them and
removes them again.

Several sets, each from its own writer, vote (`write_test_sets`,
`run_test_sets`): measured on saved benchmark projects, a wrong test turns
up in one set of three, a real bug in all three, so a project fails only
when most sets fail (docs/benchmark/independent-tests-replay-0.1.24.md).

Report only, in this first version: the result is a line under the verdict
and a field of the outcome; the verdict and the exit code don't change.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path

from .bench_tasks import HIDDEN_DIR_NAME, run_test_folder, test_language
from .config import Config
from .project_env import CommandRunner

WRITER_USAGE_ID = "certo:test-writer"
NO_TESTS_FILE = "NO_TESTS.txt"
# The writer's scratch folder: the project before the build, and its tests.
PROJECT_DIR = "project_before"
TESTS_DIR = "new_tests"
# The writer needs few steps: read a few files, write a few, finish.
_WRITER_MAX_STEPS = 40
# The copy of the project the writer reads: what it needs is code, not
# environments, packages, build output or history. Capped so a large
# repository can't flood the writer's context.
_SKIPPED_DIRS = frozenset(
    {".git", ".certo", ".venv", "venv", "node_modules", "__pycache__", "target", "dist", "build"}
)
_MAX_FILE_BYTES = 200_000
_MAX_COPY_BYTES = 5_000_000

WRITER_INSTRUCTIONS = """\
You write tests for a programming task that another agent will do later. \
You will never see its code. Your tests are run on its finished work, to \
check it did what the task asks.

Rules:
- The folder {project_dir} holds the project as it is now, before that \
agent starts (it may be empty: a new project). Read it to learn the names \
the task refers to. Never change it, and never write into it.
- Test only what the task states exactly, using names from the task or \
from the existing code: files, modules, functions, classes, \
commands, endpoints, their arguments and outputs, and the rules the task \
gives. Never guess a name neither of them gives.
- Prefer the rules a quick implementation would get wrong: edge cases, \
limits, error cases, exact formats the task spells out.
- Choose the language and test tool from the task: Python with pytest \
(files named test_*.py), Node with node:test (files ending in .js), Go \
(files ending in _test.go, in their own package that imports the project \
by its module path), Rust (integration test files ending in .rs that use \
the crate by its name).
- Your files are copied into a folder named .certo_hidden_tests at the top \
of the finished project and run from there. In Python, import project \
modules by their name from the project's top folder. In Node, import \
project files with paths starting with ../. In Go and Rust, use the module \
path or crate name the task gives.
- Write your test files directly in the folder {tests_dir} (an absolute \
path), with the file editor. No subfolders, no other files, no solution \
code. Files written anywhere else are lost.
- Keep it small: at most 15 tests, each checking one stated rule.
- If the task doesn't name what to call (functions, commands, endpoints, \
files) and the existing code doesn't either, or the language is unclear, \
or you would need a Go module path or Rust crate name you can't find, \
write no tests. Instead write {tests_dir}/NO_TESTS.txt with one line saying \
why.
- When you are done, finish.

The task:

"""


@dataclass(frozen=True)
class WrittenTests:
    """What the test writer left: a folder of tests, or the reason it has none."""

    folder: Path
    model: str
    files: tuple[str, ...] = ()
    language: str | None = None
    hashes: dict[str, str] = field(default_factory=dict)
    reason: str = ""  # why there are no tests Certo can run
    metrics: dict[str, dict] = field(default_factory=dict)

    @property
    def runnable(self) -> bool:
        return self.language is not None


@dataclass(frozen=True)
class IndependentTestsResult:
    """The independent tests' result on the finished project."""

    status: str  # passed | failed | split | error | none
    summary: str
    model: str
    output: str = ""
    # With several sets: each set's own result, in order.
    sets: tuple[IndependentTestsResult, ...] = ()


# (prompt, scratch folder, cfg, usage_id) -> {usage_id: metrics}
WriterRun = Callable[[str, Path, Config, str], dict[str, dict]]


def _run_writer_conversation(
    prompt: str, scratch: Path, cfg: Config, usage_id: str
) -> dict[str, dict]:
    """The real writer: a conversation with only the file editor (and
    finish), in `scratch`, kept in memory. No AgentContext, so no skills."""
    from openhands.sdk import Agent, Conversation
    from openhands.tools.file_editor import FileEditorTool
    from openhands.tools.preset.default import get_default_tools

    from .llm import build_llm

    tools = [t for t in get_default_tools(enable_browser=False) if t.name == FileEditorTool.name]
    agent = Agent(
        llm=build_llm(cfg, usage_id=usage_id), tools=tools, include_default_tools=["FinishTool"]
    )
    conversation = Conversation(
        agent=agent,
        workspace=str(scratch),
        persistence_dir=None,
        visualizer=None,
        max_iteration_per_run=_WRITER_MAX_STEPS,
    )
    try:
        conversation.send_message(prompt)
        conversation.run()
    finally:
        stats = conversation.conversation_stats.usage_to_metrics
        metrics = {uid: m.get() for uid, m in stats.items()}
    return metrics


def copy_project(project: Path, target: Path) -> None:
    """A read-only copy of `project` for the writer: regular files only,
    without environments, packages, build output, history or `.certo/`,
    and no file or total beyond the caps."""
    target.mkdir(parents=True, exist_ok=True)
    if not project.is_dir():
        return
    total = 0
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIPPED_DIRS)
        current = Path(dirpath)
        for name in sorted(filenames):
            source = current / name
            if source.is_symlink() or not source.is_file():
                continue
            size = source.stat().st_size
            if size > _MAX_FILE_BYTES or total + size > _MAX_COPY_BYTES:
                continue
            destination = target / source.relative_to(project)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            total += size


def write_tests(
    task: str,
    cfg: Config,
    scratch: Path,
    *,
    project: Path | None = None,
    usage_id: str = WRITER_USAGE_ID,
    run_writer: WriterRun | None = None,
) -> WrittenTests:
    """Have `cfg`'s model write tests for `task` into `scratch/new_tests`,
    with a copy of `project` as it is now in `scratch/project_before`
    (`scratch` is outside the project). Never raises for a model failure: the result then
    says why there are no tests."""
    scratch = scratch.resolve()
    folder = scratch / TESTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    before = scratch / PROJECT_DIR
    if project is not None:
        copy_project(project, before)
    else:
        before.mkdir(exist_ok=True)
    run = run_writer or _run_writer_conversation
    metrics: dict[str, dict] = {}
    try:
        instructions = WRITER_INSTRUCTIONS.format(tests_dir=folder, project_dir=before)
        metrics = run(instructions + task.strip() + "\n", scratch, cfg, usage_id)
    except Exception as exc:  # noqa: BLE001 - reported, never fatal to the run
        return WrittenTests(
            folder=folder,
            model=cfg.model,
            reason=f"the test writer stopped with an error ({type(exc).__name__}: {exc})",
        )
    files = tuple(
        sorted(p.name for p in folder.iterdir() if p.is_file() and p.name != NO_TESTS_FILE)
    )
    hashes = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in files}
    language = test_language(folder)
    reason = ""
    if language is None:
        note = folder / NO_TESTS_FILE
        if note.is_file():
            reason = note.read_text(encoding="utf-8", errors="replace").strip()
        elif files:
            reason = f"its files aren't tests Certo can run ({', '.join(files)})"
        else:
            reason = "the test writer wrote nothing"
    return WrittenTests(
        folder=folder,
        model=cfg.model,
        files=files,
        language=language,
        hashes=hashes,
        reason=reason,
        metrics=metrics,
    )


@dataclass(frozen=True)
class TestSets:
    """Every set of tests written for one run, under one scratch folder."""

    scratch: Path
    sets: tuple[WrittenTests, ...]

    @property
    def model(self) -> str:
        return self.sets[0].model if self.sets else ""

    @property
    def metrics(self) -> dict[str, dict]:
        merged: dict[str, dict] = {}
        for written in self.sets:
            merged.update(written.metrics)
        return merged

    @property
    def usage_ids(self) -> list[str]:
        return [set_usage_id(k) for k in range(1, len(self.sets) + 1)]


def set_usage_id(k: int) -> str:
    """The writer of set `k` (from 1): `certo:test-writer`, then `-2`, `-3`."""
    return WRITER_USAGE_ID if k == 1 else f"{WRITER_USAGE_ID}-{k}"


def write_test_sets(
    task: str,
    cfg: Config,
    scratch: Path,
    *,
    count: int,
    project: Path | None = None,
    parallel: bool = True,
    run_writer: WriterRun | None = None,
) -> TestSets:
    """`count` independent writers, each in `scratch/set<k>` with its own
    copy of the project; at the same time when `parallel` (a local model
    server answers one at a time, so the caller passes False for one)."""
    scratch = scratch.resolve()

    def one(k: int) -> WrittenTests:
        return write_tests(
            task,
            cfg,
            scratch / f"set{k}",
            project=project,
            usage_id=set_usage_id(k),
            run_writer=run_writer,
        )

    numbers = range(1, count + 1)
    if parallel and count > 1:
        with ThreadPoolExecutor(count) as pool:
            sets = tuple(pool.map(one, numbers))
    else:
        sets = tuple(one(k) for k in numbers)
    return TestSets(scratch=scratch, sets=sets)


def failing_sets_needed(count: int) -> int:
    """How many sets must fail for the result to be `failed`: most of them
    (1 of 1, 2 of 2, 2 of 3, 3 of 4, 3 of 5)."""
    return count // 2 + 1


def run_test_sets(
    written: TestSets, workspace: str | Path, runner: CommandRunner | None = None
) -> IndependentTestsResult:
    """Run every set on the finished project and vote. One set: its own
    result. Several: `failed` when most of the sets failed, `split` when
    some did but fewer, `passed` when every set that ran passed; a set that
    couldn't run or has no tests counts as not failing."""
    results = tuple(run_independent_tests(w, workspace, runner) for w in written.sets)
    if len(results) == 1:
        return results[0]
    ran = [r for r in results if r.status in ("passed", "failed")]
    failed = sum(r.status == "failed" for r in ran)
    count = len(results)
    if not ran:
        return replace(results[0], sets=results)
    if failed >= failing_sets_needed(count):
        status = "failed"
    elif failed:
        status = "split"
    else:
        status = "passed"
    summary = f"{failed} of {count} sets failed" if failed else f"{len(ran)} of {count} sets passed"
    return IndependentTestsResult(status, summary, written.model, sets=results)


def run_independent_tests(
    written: WrittenTests, workspace: str | Path, runner: CommandRunner | None = None
) -> IndependentTestsResult:
    """Run the written tests on the finished project and take them out
    again. A test file changed since it was written is not run."""
    if not written.runnable:
        return IndependentTestsResult("none", written.reason, written.model)
    for name, digest in written.hashes.items():
        path = written.folder / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return IndependentTestsResult(
                "error", f"{name} changed after it was written; not run", written.model
            )
    result = run_test_folder(
        written.folder, workspace, runner, language=written.language, clean_up=True
    )
    return IndependentTestsResult(result.status, result.summary, written.model, result.output)


def failing_tests(result: IndependentTestsResult, limit: int = 5) -> list[str]:
    """The failing tests' names, as each test tool prints them: pytest's
    `FAILED file::test`, `node --test`'s `not ok N - name`, `go test`'s
    `--- FAIL: Name`, `cargo test`'s `test name ... FAILED`. A pytest path
    starts at the tests' folder: through a symlinked project path (macOS's
    `/var`), pytest prints it relative to the real one, `../../var/...`."""
    found = []
    for raw in result.output.splitlines():
        line = raw.strip()
        if line.startswith("FAILED "):
            name = line.removeprefix("FAILED ").split(" - ")[0]
            marker = f"{HIDDEN_DIR_NAME}/"
            found.append(marker + name.split(marker, 1)[1] if marker in name else name)
        elif line.startswith("not ok ") and " - " in line:
            found.append(line.split(" - ", 1)[1])
        elif line.startswith("--- FAIL: "):
            found.append(line.removeprefix("--- FAIL: ").split(" ")[0])
        elif line.startswith("test ") and line.endswith(" ... FAILED"):
            found.append(line.removeprefix("test ").removesuffix(" ... FAILED"))
    return found[:limit]


def report_line(result: IndependentTestsResult) -> str:
    """The line under the verdict."""
    if result.sets and result.status in ("passed", "failed", "split"):
        return (
            f"Independent tests: {result.status}, {result.summary} "
            f"(written from the task by {result.model}; report only)."
        )
    if result.status == "none":
        return f"Independent tests: none ({result.summary})."
    if result.status == "error":
        return f"Independent tests: couldn't run ({result.summary})."
    return (
        f"Independent tests: {result.status}, {result.summary} "
        f"(written from the task by {result.model}; report only)."
    )


def set_lines(result: IndependentTestsResult, limit: int = 5) -> list[str]:
    """With several sets: one line per set, naming its failing tests."""
    lines = []
    for k, one in enumerate(result.sets, start=1):
        names = failing_tests(one, limit)
        detail = f": {', '.join(names)}" if names else ""
        lines.append(f"set {k}: {one.status} ({one.summary}){detail}")
    return lines
