"""Custom tool: let the agent run the project's main check.

The `run_tests` tool runs one check (pytest, `npm run build`, `go test`,
...) and reports it to the agent. The verification itself, which Certo also
runs after the agent finishes, lives in `certo/verification.py`: it doesn't
import the SDK, so `certo verify` starts without loading it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from openhands.sdk import Action, ImageContent, Observation, TextContent, ToolDefinition
from openhands.sdk.tool import Tool, ToolExecutor, register_tool
from pydantic import Field

from certo.project_env import LocalRunner
from certo.verification import (
    _last_nonblank_line,
    detect_project,
    discover_verification_plan,
    execute_check,
    prepare_python_env,
)

_FAILURE_LINE_RE = re.compile(r"^(?:FAILED|ERROR) (.+)$", re.MULTILINE)
_COUNT_RE = re.compile(r"(\d+) (passed|failed|errors?|skipped)")


def _parse_counts(summary_line: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for num, kind in _COUNT_RE.findall(summary_line):
        key = "errors" if kind.startswith("error") else kind
        counts[key] += int(num)
    return counts


class RunTestsAction(Action):
    path: str = Field(
        default="",
        description=(
            "Optional test path or node id to run, relative to the workspace "
            "(e.g. 'tests/test_config.py' or 'tests/test_config.py::test_foo'). "
            "Python projects only — empty runs the full suite."
        ),
    )


class RunTestsObservation(Observation):
    # "pytest" | "npm_build" | "go" | "rust" | "java-maven" | "java-gradle" |
    # "ambiguous" | "unknown" | "none" (couldn't verify at all, e.g. npm missing)
    check_kind: str = "pytest"
    exit_code: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    failures: list[str] = Field(default_factory=list)
    summary: str = ""
    output: str = ""

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        if self.check_kind == "pytest":
            lines = [self.summary or f"pytest exited with code {self.exit_code}"]
            if self.failures:
                lines.append("Failures:")
                lines.extend(f"- {failure}" for failure in self.failures)
            return [TextContent(text="\n".join(lines))]
        lines = [self.summary or f"verification exited with code {self.exit_code}"]
        if self.exit_code != 0 and self.output:
            lines.append(self.output)
        return [TextContent(text="\n".join(lines))]


class RunTestsExecutor(ToolExecutor[RunTestsAction, RunTestsObservation]):
    def __init__(self, working_dir: str):
        self._working_dir = working_dir

    def __call__(self, action: RunTestsAction, conversation=None) -> RunTestsObservation:
        detection = detect_project(self._working_dir)
        if detection.language == "python":
            return self._run_pytest(action, detection.root)
        if detection.language == "node":
            return self._run_npm_build(detection.root)
        # Go/Rust/Java/unknown: the agent-facing tool always runs exactly
        # one check (its contract, unchanged) — reuse the same plan/execute
        # pipeline the harness's own post-hoc verification uses (stages 2-3
        # below) instead of a second, separate detection path, and adapt its
        # richer `CheckOutcome` into this tool's legacy `Observation` shape.
        plan = discover_verification_plan(detection)
        primary = next((spec for spec in plan if spec.primary), plan[0])
        outcome = execute_check(primary)
        # A timed-out check has no exit code; report it as nonzero so the
        # agent is shown the output and doesn't read it as a pass.
        exit_code = outcome.exit_code
        if exit_code is None:
            exit_code = 1 if outcome.status == "timed_out" else 0
        return RunTestsObservation(
            check_kind=detection.language,
            exit_code=exit_code,
            summary=outcome.summary,
            output=outcome.output,
        )

    def _run_pytest(self, action: RunTestsAction, run_dir: str) -> RunTestsObservation:
        # The project's own environment, never this process's interpreter
        # (see project_env.py). Runs wherever this tool runs: the host under
        # local execution, the container under Docker.
        runner = LocalRunner()
        state = prepare_python_env(run_dir, runner, stop_at=self._working_dir, install_pytest=True)
        if state.env is None or "pytest" not in state.modules:
            return RunTestsObservation(
                check_kind="none",
                summary=state.pytest_unavailable_reason or "pytest is not available",
            )
        cmd = [*state.env.python, "-m", "pytest", "-q"]
        if action.path:
            cmd.append(action.path)
        result = runner.run(
            cmd, cwd=run_dir, env=state.env.env_vars(runner.base_path()), timeout=300
        )
        if result.returncode is None:
            return RunTestsObservation(
                check_kind="none",
                summary=(
                    "pytest timed out after 300s"
                    if result.timed_out
                    else f"pytest could not be run: {result.error}"
                ),
                output=result.output[-4000:],
            )
        output = result.output
        if state.notices:
            output = "\n".join(state.notices) + "\n" + output
        summary = _last_nonblank_line(result.output)
        counts = _parse_counts(summary)
        failures = _FAILURE_LINE_RE.findall(output)
        return RunTestsObservation(
            check_kind="pytest",
            exit_code=result.returncode,
            passed=counts["passed"],
            failed=counts["failed"],
            errors=counts["errors"],
            failures=failures,
            summary=summary,
            output=output[-4000:],
        )

    def _run_npm_build(self, run_dir: str) -> RunTestsObservation:
        runner = LocalRunner()
        npm = runner.which("npm")
        if npm is None:
            return RunTestsObservation(
                check_kind="none",
                summary="npm not found on PATH; cannot verify the build",
            )
        result = runner.run([npm, "run", "build"], cwd=run_dir, timeout=300)
        output = result.output
        if result.returncode is None:
            return RunTestsObservation(
                check_kind="npm_build",
                exit_code=1,
                summary="npm run build timed out"
                if result.timed_out
                else f"npm could not run: {result.error}",
                output=output[-4000:],
            )
        summary = (
            "npm run build succeeded"
            if result.returncode == 0
            else f"npm run build failed (exit {result.returncode})"
        )
        return RunTestsObservation(
            check_kind="npm_build",
            exit_code=result.returncode,
            summary=summary,
            output=output[-4000:],
        )


class RunTestsTool(ToolDefinition[RunTestsAction, RunTestsObservation]):
    """Verify the project actually works, whatever language it's written in
    (Python, Node/JS/TS, Go, Rust, or Java). Runs the project's single
    primary check — its test suite (Python: pytest; Go: `go test ./...`;
    Rust: `cargo test`; Java: Maven/Gradle `test`) or, for a Node project
    with no test script but a `build` script (e.g. Vite/React), `npm run
    build` — catching compile/parse errors a test suite might never
    exercise. Reports the command's exit status and raw output; for pytest,
    also structured pass/fail/error counts and failing node ids."""

    @classmethod
    def create(cls, conv_state, **params) -> Sequence[ToolDefinition]:
        working_dir = str(conv_state.workspace.working_dir)
        return [
            cls(
                description=cls.__doc__ or "",
                action_type=RunTestsAction,
                observation_type=RunTestsObservation,
                executor=RunTestsExecutor(working_dir),
            )
        ]


# Registering at import time (not inside build_run_tests_tool) means importing
# this module is enough to make the tool available — which is what lets a
# containerized agent-server register it via `--import-modules
# certo.custom_tools` (see docker/agent-server.Dockerfile), not just the
# local process that calls build_run_tests_tool() directly.
register_tool(RunTestsTool.name, RunTestsTool)


def build_run_tests_tool() -> Tool:
    return Tool(name=RunTestsTool.name)
