import pytest

from certo import checkpoints as cp
from certo import cli

pytestmark = pytest.mark.skipif(not cp.git_available(), reason="git isn't installed")


def _project(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    (project / "a.py").write_text("a = 1\n")
    cp.snapshot(str(project), "before the agent")
    (project / "a.py").write_text("a = 2\n")
    (project / "new.py").write_text("n = 1\n")
    cp.snapshot(str(project), "checks 1: failed")
    return project


def test_checkpoints_lists_them(tmp_path, capsys):
    project = _project(tmp_path)

    assert cli.main(["checkpoints", str(project)]) == 0

    out = capsys.readouterr().out
    assert f"Checkpoints of {project}" in out
    assert "  1  " in out and "before the agent" in out
    assert "  2  " in out and "checks 1: failed" in out


def test_checkpoints_with_none(tmp_path, capsys):
    assert cli.main(["checkpoints", str(tmp_path)]) == 0
    assert "No checkpoints in" in capsys.readouterr().out


def test_rollback_shows_the_changes_and_asks(tmp_path, capsys):
    from certo.checkpoints_cmd import rollback_main

    project = _project(tmp_path)

    assert rollback_main(["1", str(project)], ask=lambda _q: "n") == 1
    assert (project / "a.py").read_text() == "a = 2\n"
    assert rollback_main(["1", str(project)], ask=lambda _q: "y") == 0

    out = capsys.readouterr().out
    assert "restored: a.py" in out and "deleted: new.py" in out
    assert "Nothing changed." in out
    assert "Done: the files are as they were at checkpoint 1." in out
    assert "`certo rollback 2` undoes it." in out
    assert (project / "a.py").read_text() == "a = 1\n"
    assert not (project / "new.py").exists()


def test_rollback_without_a_terminal_needs_yes(tmp_path, capsys, monkeypatch):
    project = _project(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    assert cli.main(["rollback", "1", str(project)]) == 1
    assert "add --yes" in capsys.readouterr().err
    assert cli.main(["rollback", "1", str(project), "--yes"]) == 0
    assert (project / "a.py").read_text() == "a = 1\n"


def test_rollback_to_a_missing_number(tmp_path, capsys):
    project = _project(tmp_path)

    assert cli.main(["rollback", "9", str(project), "--yes"]) == 1
    assert "no checkpoint 9" in capsys.readouterr().err
