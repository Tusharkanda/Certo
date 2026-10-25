"""Snapshots of the project during a run, and putting one back.

Certo keeps its own git repository in `.certo/checkpoints/`, with the
project folder as its work tree, and commits a snapshot before the agent
starts, at every verification (the first and each fix attempt; each rung
with `--escalate`) and when the run ends. `certo checkpoints` lists them,
`certo rollback N` puts the project's files back as they were at
snapshot N (after taking one of the files as they are, so a rollback can
be undone too). Certo never rolls back on its own.

The project's own git repository, if any, is never touched: every git
command runs with this repository's `GIT_DIR` and its own index, so no
commit, branch, stash or index of the user's changes. Left out of a
snapshot: what the project's `.gitignore` ignores, environments and caches
(`SKIP_DIRS`), Certo's `.certo/` folder, and files over `MAX_FILE_BYTES`.

Best effort: without git, or when a git command fails, there is no
snapshot and the run goes on. Stdlib only, no SDK import.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CHECKPOINTS_DIR = os.path.join(".certo", "checkpoints")
# Environments, caches and build output: large, and rebuilt by the tools.
SKIP_DIRS = (
    ".certo",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    "target",
    ".gradle",
)
MAX_FILE_BYTES = 10 * 1024 * 1024
_GIT_TIMEOUT_SECONDS = 120
_SEPARATOR = "\x1f"


class CheckpointError(RuntimeError):
    """A checkpoint command couldn't do what it was asked. User-facing."""


@dataclass(frozen=True)
class Checkpoint:
    number: int
    label: str
    commit: str
    when: str  # ISO 8601, local time


def git_available() -> bool:
    return shutil.which("git") is not None


def _git_dir(project: str) -> str:
    return os.path.join(project, CHECKPOINTS_DIR)


def _git(project: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "GIT_DIR": _git_dir(project),
        "GIT_WORK_TREE": project,
        "GIT_INDEX_FILE": os.path.join(_git_dir(project), "index"),
        # Never the user's hooks, templates or signing settings.
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    result = subprocess.run(
        ["git", *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    if check and result.returncode != 0:
        raise CheckpointError(f"git {args[0]} failed: {result.stderr.strip() or result.stdout}")
    return result


def _ensure_repo(project: str) -> None:
    if os.path.isfile(os.path.join(_git_dir(project), "HEAD")):
        return
    os.makedirs(_git_dir(project), exist_ok=True)
    _git(project, "init", "--quiet")
    for key, value in (
        ("user.name", "Certo"),
        ("user.email", "certo@localhost"),
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", os.devnull),
    ):
        _git(project, "config", key, value)


def _write_excludes(project: str) -> list[str]:
    """Environments, caches and large files go in the repository's own
    exclude file (the project's `.gitignore` applies on its own). Returns
    the large files left out."""
    large = []
    for dirpath, dirs, files in os.walk(project):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and d != ".git")
        for name in files:
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    large.append(os.path.relpath(path, project).replace(os.sep, "/"))
            except OSError:
                continue
    lines = [f"{d}/" for d in SKIP_DIRS] + ["/" + path for path in sorted(large)]
    info = os.path.join(_git_dir(project), "info")
    os.makedirs(info, exist_ok=True)
    with open(os.path.join(info, "exclude"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return large


def snapshot(project: str, label: str, *, always: bool = False) -> Checkpoint | None:
    """Commit the project's files as they are now. None when nothing
    changed since the last snapshot (unless `always`). Raises
    CheckpointError when git fails."""
    project = os.path.abspath(project)
    _ensure_repo(project)
    _write_excludes(project)
    _git(project, "add", "--all", "--", ".")
    has_head = _git(project, "rev-parse", "--verify", "--quiet", "HEAD", check=False)
    if has_head.returncode == 0 and not always:
        unchanged = _git(project, "diff", "--cached", "--quiet", check=False)
        if unchanged.returncode == 0:
            return None
    number = len(list_checkpoints(project)) + 1
    _git(project, "commit", "--quiet", "--allow-empty", "--no-verify", "-m", label)
    return list_checkpoints(project)[number - 1]


def safe_snapshot(project: str, label: str, *, always: bool = False) -> Checkpoint | None:
    """`snapshot`, never raising: a run doesn't stop for a snapshot."""
    if not git_available():
        return None
    try:
        return snapshot(project, label, always=always)
    except (CheckpointError, OSError, subprocess.SubprocessError):
        logger.warning("Could not take a checkpoint", exc_info=True)
        return None


def list_checkpoints(project: str) -> list[Checkpoint]:
    """Every snapshot, oldest first, numbered from 1."""
    project = os.path.abspath(project)
    if not os.path.isfile(os.path.join(_git_dir(project), "HEAD")):
        return []
    result = _git(
        project, "log", "--reverse", f"--format=%H{_SEPARATOR}%cI{_SEPARATOR}%s", check=False
    )
    if result.returncode != 0:  # a repository with no commit yet
        return []
    checkpoints = []
    for number, line in enumerate(result.stdout.splitlines(), start=1):
        commit, when, label = line.split(_SEPARATOR, 2)
        checkpoints.append(Checkpoint(number, label, commit, when))
    return checkpoints


def changed_files(project: str, checkpoint: Checkpoint) -> list[str]:
    """What a rollback to `checkpoint` would change, as `git diff
    --name-status` lines (M, A = would be restored, D = would be deleted),
    against the project's files as they are now."""
    project = os.path.abspath(project)
    _write_excludes(project)
    _git(project, "add", "--all", "--", ".")
    result = _git(project, "diff", "--cached", "--name-status", "-R", checkpoint.commit)
    return [line.replace("\t", " ") for line in result.stdout.splitlines()]


def rollback(project: str, number: int) -> tuple[Checkpoint | None, Checkpoint]:
    """Put the project's files back as they were at snapshot `number`.
    First snapshots the files as they are (returned first; None when they
    already match the last snapshot), then restores, then records the
    result as a snapshot of its own. Files the snapshot left out
    (`.gitignore`, environments, large files) are never touched."""
    project = os.path.abspath(project)
    checkpoints = list_checkpoints(project)
    if not 1 <= number <= len(checkpoints):
        raise CheckpointError(
            f"no checkpoint {number}; this project has {len(checkpoints)}"
            + (" (run `certo checkpoints` to list them)." if checkpoints else ".")
        )
    target = checkpoints[number - 1]
    before = snapshot(project, "before rollback")
    # Index and work tree to the snapshot's tree: tracked files that the
    # snapshot doesn't have are deleted, the others restored.
    _git(project, "read-tree", "--reset", "-u", target.commit)
    after = snapshot(project, f"rolled back to {number}", always=True)
    return before, after
