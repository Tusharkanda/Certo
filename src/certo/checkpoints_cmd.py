"""`certo checkpoints [PATH]` and `certo rollback N [PATH]`: list the
snapshots Certo took of a project during its runs, and put the project's
files back as they were at one of them (checkpoints.py).

`rollback` shows what it would change and asks first; `--yes` skips the
question (and is required when nobody can answer it). The files as they
are before a rollback become a snapshot of their own, so the rollback can
be undone with another one.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from datetime import datetime

from .checkpoints import (
    CHECKPOINTS_DIR,
    Checkpoint,
    CheckpointError,
    changed_files,
    git_available,
    list_checkpoints,
    rollback,
)

_CHANGE_WORDS = {"M": "restored", "A": "added back", "D": "deleted"}


def _when(checkpoint: Checkpoint) -> str:
    try:
        return datetime.fromisoformat(checkpoint.when).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return checkpoint.when


def _project(path: str) -> str | None:
    project = os.path.abspath(path)
    if not os.path.isdir(project):
        print(f"Error: {path} is not a directory", file=sys.stderr)
        return None
    return project


def _no_checkpoints(project: str) -> int:
    print(
        f"No checkpoints in {project}. Certo takes them during a run "
        "(CERTO_CHECKPOINTS, on by default)."
    )
    return 0


def build_checkpoints_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="certo checkpoints",
        description="List the snapshots Certo took of a project during its runs.",
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Project directory (default: current directory)."
    )
    return parser


def build_rollback_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="certo rollback",
        description=(
            "Put a project's files back as they were at one of Certo's checkpoints "
            "(see `certo checkpoints`). Your files as they are now become a checkpoint "
            "first, so a rollback can be undone."
        ),
    )
    parser.add_argument("number", type=int, help="The checkpoint's number.")
    parser.add_argument(
        "path", nargs="?", default=".", help="Project directory (default: current directory)."
    )
    parser.add_argument("--yes", action="store_true", help="Don't ask before changing files.")
    return parser


def checkpoints_main(argv: list[str]) -> int:
    args = build_checkpoints_parser().parse_args(argv)
    project = _project(args.path)
    if project is None:
        return 1
    if not git_available():
        print("Error: checkpoints need git, which isn't installed.", file=sys.stderr)
        return 1
    checkpoints = list_checkpoints(project)
    if not checkpoints:
        return _no_checkpoints(project)
    print(f"Checkpoints of {project} (in {CHECKPOINTS_DIR}/):")
    width = len(str(checkpoints[-1].number))
    for checkpoint in checkpoints:
        print(f"  {checkpoint.number:>{width}}  {_when(checkpoint)}  {checkpoint.label}")
    print("\nPut the files back as they were at one of them: certo rollback N")
    return 0


def rollback_main(argv: list[str], ask: Callable[[str], str] | None = None) -> int:
    args = build_rollback_parser().parse_args(argv)
    project = _project(args.path)
    if project is None:
        return 1
    if not git_available():
        print("Error: checkpoints need git, which isn't installed.", file=sys.stderr)
        return 1
    checkpoints = list_checkpoints(project)
    if not checkpoints:
        return _no_checkpoints(project)
    if not 1 <= args.number <= len(checkpoints):
        print(
            f"Error: no checkpoint {args.number}; {project} has 1 to {len(checkpoints)} "
            "(see `certo checkpoints`).",
            file=sys.stderr,
        )
        return 1
    target = checkpoints[args.number - 1]
    try:
        changes = changed_files(project, target)
    except CheckpointError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if not changes:
        print(f"Nothing to change: the files already match checkpoint {target.number}.")
        return 0
    print(f"Rolling back {project} to checkpoint {target.number} ({target.label}):")
    for line in changes:
        kind, _, path = line.partition(" ")
        print(f"  {_CHANGE_WORDS.get(kind[:1], kind)}: {path}")
    if not args.yes:
        if ask is None:
            if not sys.stdin.isatty():
                sys.stdout.flush()  # the list above comes first
                print("Error: add --yes to roll back without a question.", file=sys.stderr)
                return 1
            ask = input
        if ask("Go ahead? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Nothing changed.")
            return 1
    try:
        before, _ = rollback(project, target.number)
    except CheckpointError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Done: the files are as they were at checkpoint {target.number}.")
    undo = before.number if before is not None else checkpoints[-1].number
    print(
        f"Your files before the rollback are checkpoint {undo}: `certo rollback {undo}` undoes it."
    )
    return 0
