import subprocess

import pytest

from certo import checkpoints as cp

pytestmark = pytest.mark.skipif(not cp.git_available(), reason="git isn't installed")


def _project(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    (project / "a.py").write_text("a = 1\n")
    return project


def test_snapshots_are_numbered_and_unchanged_files_take_none(tmp_path):
    project = _project(tmp_path)

    first = cp.snapshot(str(project), "before the agent")
    (project / "a.py").write_text("a = 2\n")
    second = cp.snapshot(str(project), "checks 1: failed")
    third = cp.snapshot(str(project), "finished: failed")

    assert (first.number, first.label) == (1, "before the agent")
    assert (second.number, second.label) == (2, "checks 1: failed")
    assert third is None
    assert [c.label for c in cp.list_checkpoints(str(project))] == [
        "before the agent",
        "checks 1: failed",
    ]


def test_a_rollback_restores_deletes_and_can_be_undone(tmp_path):
    project = _project(tmp_path)
    cp.snapshot(str(project), "before the agent")
    (project / "a.py").write_text("a = 2\n")
    (project / "new.py").write_text("n = 1\n")

    assert cp.changed_files(str(project), cp.list_checkpoints(str(project))[0]) == [
        "M a.py",
        "D new.py",
    ]
    before, after = cp.rollback(str(project), 1)

    assert (project / "a.py").read_text() == "a = 1\n"
    assert not (project / "new.py").exists()
    assert (before.label, after.label) == ("before rollback", "rolled back to 1")
    cp.rollback(str(project), before.number)  # undo
    assert (project / "a.py").read_text() == "a = 2\n"
    assert (project / "new.py").read_text() == "n = 1\n"


def test_the_projects_own_git_repository_is_never_touched(tmp_path):
    project = _project(tmp_path)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], cwd=project, check=True)
    subprocess.run([*git, "add", "a.py"], cwd=project, check=True)
    subprocess.run([*git, "commit", "-qm", "init"], cwd=project, check=True)
    (project / "a.py").write_text("a = 2\n")  # an uncommitted change
    (project / "b.py").write_text("b = 1\n")

    def state():
        return [
            subprocess.run(args, cwd=project, capture_output=True, text=True).stdout
            for args in (
                ["git", "log", "--format=%H"],
                ["git", "status", "--porcelain", "--untracked-files=no"],
                ["git", "stash", "list"],
                ["git", "branch", "--all"],
            )
        ]

    before = state()
    cp.snapshot(str(project), "before the agent")
    (project / "b.py").write_text("b = 2\n")
    cp.snapshot(str(project), "checks 1: failed")
    cp.rollback(str(project), 1)

    assert state() == before
    assert (project / "b.py").read_text() == "b = 1\n"


def test_environments_ignored_files_and_large_files_are_left_out(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "MAX_FILE_BYTES", 100)
    project = _project(tmp_path)
    (project / ".gitignore").write_text("*.log\n")
    (project / "run.log").write_text("log\n")
    (project / ".venv").mkdir()
    (project / ".venv" / "lib.py").write_text("x\n")
    (project / "big.bin").write_bytes(b"x" * 200)

    cp.snapshot(str(project), "before the agent")
    (project / "run.log").unlink()
    (project / "big.bin").write_bytes(b"y" * 300)
    cp.snapshot(str(project), "later")
    (project / "a.py").write_text("a = 2\n")
    cp.rollback(str(project), 1)

    assert (project / ".venv" / "lib.py").exists()
    assert not (project / "run.log").exists()  # never in a snapshot, never restored
    assert (project / "big.bin").read_bytes() == b"y" * 300
    assert (project / "a.py").read_text() == "a = 1\n"


def test_rollback_to_a_missing_number_is_an_error(tmp_path):
    project = _project(tmp_path)
    cp.snapshot(str(project), "before the agent")

    with pytest.raises(cp.CheckpointError, match="no checkpoint 5; this project has 1"):
        cp.rollback(str(project), 5)


def test_safe_snapshot_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cp, "snapshot", lambda *a, **k: (_ for _ in ()).throw(cp.CheckpointError("x"))
    )

    assert cp.safe_snapshot(str(tmp_path), "x") is None
