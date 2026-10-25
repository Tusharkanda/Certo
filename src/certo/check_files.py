"""Did the agent change the files the project's checks rely on?

`verified` means the project's own checks passed after the run. An agent
can make them pass by weakening them: editing a test, deleting one, or
switching a lint rule off. Certo copies the check files before the run
(test files, and the settings files that steer tests, build and lint)
and, after a `verified` run, reports each one the agent changed or
deleted, with the lines removed and added. New files aren't reported:
adding tests is normal. Report only; the task may have asked for it.
"""

from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass

from .escalation import workspace_listing

_TEST_DIRS = frozenset({"tests", "test", "__tests__", "spec", "specs"})
_TEST_FILE = re.compile(
    r"^(test_.+\.py|.+_test\.(py|go)|.+\.(test|spec)\.[cm]?[jt]sx?|conftest\.py"
    r"|.+Tests?\.(java|kt))$"
)
_SETTINGS_FILES = frozenset(
    {
        "pyproject.toml",
        "setup.cfg",
        "pytest.ini",
        "tox.ini",
        "ruff.toml",
        ".ruff.toml",
        "mypy.ini",
        ".mypy.ini",
        ".flake8",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "Makefile",
    }
)
_SETTINGS_PREFIXES = (
    "tsconfig",
    "jest.config",
    "vitest.config",
    "eslint.config",
    ".eslintrc",
    ".golangci",
)
# Larger files are left out of the copy (a check file is rarely this big).
_MAX_FILE_BYTES = 1_000_000
_LISTED_LIMIT = 5


def is_check_file(path: str) -> bool:
    """Whether `path` (relative to the project) is a test file or a file
    that steers the project's checks."""
    parts = path.replace(os.sep, "/").split("/")
    name = parts[-1]
    return (
        any(part in _TEST_DIRS for part in parts[:-1])
        or bool(_TEST_FILE.match(name))
        or name in _SETTINGS_FILES
        or name.startswith(_SETTINGS_PREFIXES)
    )


def snapshot_check_files(root: str) -> dict[str, bytes]:
    """The content of every check file under `root`, by relative path."""
    snapshot: dict[str, bytes] = {}
    for path, (size, _mtime) in workspace_listing(root).items():
        if size > _MAX_FILE_BYTES or not is_check_file(path):
            continue
        try:
            with open(os.path.join(root, path), "rb") as f:
                snapshot[path] = f.read()
        except OSError:
            continue
    return snapshot


@dataclass(frozen=True)
class CheckFileChange:
    path: str
    deleted: bool
    removed: int  # lines
    added: int  # lines

    @property
    def described(self) -> str:
        if self.deleted:
            return f"{self.path} (deleted)"
        return f"{self.path} ({_lines(self.removed)} removed, {_lines(self.added)} added)"


def _lines(count: int) -> str:
    return f"{count} line" if count == 1 else f"{count} lines"


def check_file_changes(root: str, before: dict[str, bytes]) -> tuple[CheckFileChange, ...]:
    """Each check file in `before` that is now different or gone."""
    changes = []
    for path, old in sorted(before.items()):
        try:
            with open(os.path.join(root, path), "rb") as f:
                new = f.read()
        except FileNotFoundError:
            changes.append(CheckFileChange(path, True, len(old.splitlines()), 0))
            continue
        except OSError:
            continue
        if new == old:
            continue
        removed = added = 0
        matcher = difflib.SequenceMatcher(None, old.splitlines(), new.splitlines(), autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                removed += i2 - i1
                added += j2 - j1
        changes.append(CheckFileChange(path, False, removed, added))
    return tuple(changes)


def changes_note(changes: tuple[CheckFileChange, ...]) -> str:
    """The limitation line for a `verified` run that changed check files."""
    listed = ", ".join(c.described for c in changes[:_LISTED_LIMIT])
    more = len(changes) - _LISTED_LIMIT
    if more > 0:
        listed += f", and {more} more"
    count = "1 file" if len(changes) == 1 else f"{len(changes)} files"
    return (
        f"The agent changed {count} the checks rely on: {listed}. The checks "
        "passed on the changed files; read the changes before you trust them."
    )
