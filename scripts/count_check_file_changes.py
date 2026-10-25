"""Count how often benchmark runs changed the starter's check files (TODO.md,
"Changed check files: the rest").

Each saved project in a `certo bench` results folder is compared with its
task's starter, the way a run's check files are compared since 0.1.24
(check_files.py): every starter test file or check setting the agent
changed or deleted, with lines removed and added. The hidden-test result
says whether the work was right. No model is called; the results folders
are only read.

    uv run python scripts/count_check_file_changes.py --results bench-results \\
        --out bench-results/check-file-changes.md
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from certo.bench_tasks import BUILTIN_TASKS_DIR, BenchTask, load_tasks, prepare_workspace
from certo.check_files import (
    _SETTINGS_FILES,
    _SETTINGS_PREFIXES,
    check_file_changes,
    snapshot_check_files,
)


def _starter_changed(task: BenchTask) -> datetime:
    """When the task's starter last changed in git."""
    out = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", "starter"],
        cwd=task.path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    # A task with no starter starts from an empty folder.
    return datetime.fromisoformat(out) if out else datetime.min.replace(tzinfo=UTC)


def _run_started(folder: Path, run_id: str, csv_path: Path) -> datetime:
    record = folder / "runs" / f"{run_id}.json"
    if record.is_file():
        started = json.loads(record.read_text(encoding="utf-8")).get("started_at")
        if started:
            return datetime.fromisoformat(started)
    return datetime.fromtimestamp(csv_path.stat().st_mtime, UTC)


def _rows(results: Path, tasks: dict[str, BenchTask], scratch: Path) -> list[dict]:
    starters = {}
    for name, task in tasks.items():
        path = scratch / name
        prepare_workspace(task, path)
        starters[name] = snapshot_check_files(str(path))
    changed = {name: _starter_changed(t) for name, t in tasks.items()}
    rows = []
    for csv_path in sorted(results.glob("*/results.csv")):
        folder = csv_path.parent
        for row in csv.DictReader(csv_path.open(encoding="utf-8")):
            task = row["task"]
            workspace = folder / "workspaces" / row["run_id"]
            if task not in tasks or not workspace.is_dir():
                continue
            if row["hidden_status"] not in ("passed", "failed"):
                continue
            if _run_started(folder, row["run_id"], csv_path) <= changed[task]:
                continue
            changes = check_file_changes(str(workspace), starters[task])
            rows.append(
                {
                    "id": f"{folder.name}/{row['run_id']}",
                    "task": task,
                    "verdict": row["verdict"],
                    "hidden": row["hidden_status"],
                    "starter_files": len(starters[task]),
                    "changes": changes,
                }
            )
    return rows


def _is_test(path: str) -> bool:
    name = Path(path).name
    return not (name in _SETTINGS_FILES or name.startswith(_SETTINGS_PREFIXES))


def _report(rows: list[dict]) -> str:
    def share(group: list[dict], test) -> str:
        return f"{sum(1 for r in group if test(r))} of {len(group)}"

    def any_change(r):
        return bool(r["changes"])

    def test_changed(r):
        return any(_is_test(c.path) for c in r["changes"])

    def test_lines_removed(r):
        return any(_is_test(c.path) and (c.deleted or c.removed) for c in r["changes"])

    verified = [r for r in rows if r["verdict"] == "verified"]
    groups = [
        ("All runs", rows),
        ("Verified", verified),
        ("Verified, hidden tests passed", [r for r in verified if r["hidden"] == "passed"]),
        (
            "Verified, hidden tests failed (fooled)",
            [r for r in verified if r["hidden"] == "failed"],
        ),
        ("Not verified", [r for r in rows if r["verdict"] != "verified"]),
    ]
    lines = [
        "# Check files changed by benchmark runs",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC from {len(rows)} saved projects.",
        "",
        "| Runs | Any check file changed | A starter test changed | Test lines removed or a test deleted |",
        "|---|---|---|---|",
    ]
    for label, group in groups:
        lines.append(
            f"| {label} | {share(group, any_change)} | {share(group, test_changed)} "
            f"| {share(group, test_lines_removed)} |"
        )
    lines += [
        "",
        "## Per task",
        "",
        "| Task | Starter check files | Runs | Any changed | Test lines removed |",
        "|---|---|---|---|---|",
    ]
    for task in sorted({r["task"] for r in rows}):
        group = [r for r in rows if r["task"] == task]
        lines.append(
            f"| {task} | {group[0]['starter_files']} | {len(group)} "
            f"| {sum(map(any_change, group))} | {sum(map(test_lines_removed, group))} |"
        )
    files = Counter(c.path for r in rows for c in r["changes"])
    lines += ["", "## Files changed most", "", "| File | Runs |", "|---|---|"]
    lines += [f"| `{path}` | {count} |" for path, count in files.most_common(15)]
    lines += [
        "",
        "## Verified runs that removed test lines",
        "",
        "| Run | Hidden tests | Changes |",
        "|---|---|---|",
    ]
    for r in verified:
        if test_lines_removed(r):
            described = "; ".join(c.described for c in r["changes"])
            lines.append(f"| {r['id']} | {r['hidden']} | {described} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=Path("bench-results"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    tasks = {t.name: t for t in load_tasks(BUILTIN_TASKS_DIR)}
    with tempfile.TemporaryDirectory() as scratch:
        rows = _rows(args.results, tasks, Path(scratch))
    report = _report(rows)
    args.out.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
