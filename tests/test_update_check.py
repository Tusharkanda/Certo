import json
import os

import pytest

from certo import cli, update_check
from certo.update_check import UpdateCheck, enabled, parse_version, upgrade_command

NOW = 1_800_000_000.0


def _check(tmp_path, latest="0.1.28", current="0.1.27", calls=None, prefix="/usr"):
    def fetch():
        if calls is not None:
            calls.append(1)
        return latest

    path = str(tmp_path / "certo" / "update-check.json")
    return UpdateCheck(current, path, fetch=fetch, now=lambda: NOW, prefix=prefix)


def test_a_newer_version_gives_one_line(tmp_path):
    check = _check(tmp_path).start()
    assert check.notice(wait=5) == (
        "Certo 0.1.28 is out (you have 0.1.27). To update: pip install -U certo"
    )


@pytest.mark.parametrize("latest", ["0.1.27", "0.1.26", None, "not a version"])
def test_no_line_when_up_to_date_or_unknown(tmp_path, latest):
    assert _check(tmp_path, latest=latest).start().notice(wait=5) is None


def test_the_answer_is_kept_for_a_day(tmp_path):
    calls = []
    _check(tmp_path, calls=calls).start().notice(wait=5)
    saved = json.loads((tmp_path / "certo" / "update-check.json").read_text())
    assert saved == {"checked_at": NOW, "latest": "0.1.28"}
    again = _check(tmp_path, latest="9.9.9", calls=calls).start()
    assert again.notice(wait=5).startswith("Certo 0.1.28 is out")
    assert len(calls) == 1


def test_an_old_or_broken_cache_is_checked_again(tmp_path):
    path = tmp_path / "certo" / "update-check.json"
    path.parent.mkdir()
    for content in (
        json.dumps({"checked_at": NOW - 2 * update_check.CHECK_EVERY_SECONDS, "latest": "0.1.9"}),
        "{not json",
    ):
        path.write_text(content)
        calls = []
        assert _check(tmp_path, calls=calls).start().notice(wait=5).startswith("Certo 0.1.28")
        assert calls == [1]


def test_a_failed_check_writes_nothing(tmp_path):
    assert _check(tmp_path, latest=None).start().notice(wait=5) is None
    assert not (tmp_path / "certo" / "update-check.json").exists()


@pytest.mark.parametrize(
    ("prefix", "command"),
    [
        ("/home/a/.local/share/uv/tools/certo", "uv tool upgrade certo"),
        (r"C:\Users\a\AppData\Roaming\uv\tools\certo", "uv tool upgrade certo"),
        ("/home/a/.local/share/pipx/venvs/certo", "pipx upgrade certo"),
        ("/home/a/project/.venv", "pip install -U certo"),
    ],
)
def test_the_command_matches_the_install(prefix, command):
    assert upgrade_command(prefix) == command


def test_versions():
    assert parse_version("0.1.27") == (0, 1, 27)
    assert parse_version("0.1.10") > parse_version("0.1.9")
    assert parse_version("0.1.27.dev0") is None
    assert parse_version("") is None


def test_enabled_only_on_a_terminal_outside_ci_and_not_turned_off():
    assert enabled({}, interactive=True)
    assert not enabled({}, interactive=False)
    assert not enabled({"CI": "true"}, interactive=True)
    assert not enabled({"CERTO_UPDATE_CHECK": "0"}, interactive=True)
    assert not enabled({"CERTO_UPDATE_CHECK": "false"}, interactive=True)
    assert enabled({"CERTO_UPDATE_CHECK": "1"}, interactive=True)


def test_the_cli_prints_the_line_after_the_command(monkeypatch, capsys, tmp_path):
    check = _check(tmp_path).start()
    monkeypatch.setattr(cli, "_start_update_check", lambda: check)
    monkeypatch.setattr(cli, "_main", lambda argv: 0)
    assert cli.main(["some task"]) == 0
    assert "Certo 0.1.28 is out (you have 0.1.27)" in capsys.readouterr().err


def test_the_cli_skips_the_check_for_bench(monkeypatch):
    started = []
    monkeypatch.setattr(cli, "_start_update_check", lambda: started.append(1))
    monkeypatch.setattr(cli, "_main", lambda argv: 0)
    cli.main(["bench", "--help"])
    assert started == []


def test_the_setting_in_a_dotenv_turns_it_off(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("CERTO_UPDATE_CHECK", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    (tmp_path / ".env").write_text("CERTO_UPDATE_CHECK=0\n")
    seen = []
    monkeypatch.setattr(update_check, "start", lambda environ: seen.append(environ) or None)
    cli._start_update_check()
    assert seen[0]["CERTO_UPDATE_CHECK"] == "0"
    assert "CERTO_UPDATE_CHECK" not in os.environ
