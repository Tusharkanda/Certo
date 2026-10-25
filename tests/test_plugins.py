"""plugins.py tests: which OpenHands plugins would reach a run from outside
the project, and the CLI and server refusing to start. Real SDK discovery;
the user plugin folders point at a temporary one (conftest.py)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from certo import cli, server
from certo.config import Config, ConfigError
from certo.plugins import foreign_plugins, refusal

SKILL = "---\nname: {name}\ndescription: d\n---\nPLUGIN-RULES\n"


def _plugin(folder: Path, name: str, skill: str | None = None) -> Path:
    """A plugin folder; with `skill`, one skill inside it."""
    plugin = folder / name
    plugin.mkdir(parents=True)
    (plugin / "README.md").write_text("A plugin.\n")
    if skill:
        (plugin / "skills" / skill).mkdir(parents=True)
        (plugin / "skills" / skill / "SKILL.md").write_text(SKILL.format(name=skill))
    return plugin


def _generated_project_in_a_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    _plugin(repo / ".agents" / "plugins", "repo-plugin")
    projects = repo / "projects"
    return projects / "demo", projects


def _cfg(**overrides) -> Config:
    base = dict(
        model="openai/gpt-4o",
        api_key="key",
        base_url=None,
        workspace=".",
        max_iterations=10,
        confirm_mode="never",
        execution="local",
    )
    base.update(overrides)
    return Config(**base)


def test_no_plugins_nothing_foreign(tmp_path):
    assert foreign_plugins(tmp_path / "p", tmp_path) == []


def test_a_user_plugin_is_always_foreign(tmp_path, user_plugins_dir):
    _plugin(user_plugins_dir, "mine")

    found = foreign_plugins(tmp_path / "p", tmp_path)

    assert [(p.name, p.user) for p in found] == [("mine", True)]
    assert [p.name for p in foreign_plugins(None)] == ["mine"]


def test_a_repo_plugin_is_foreign_to_a_generated_project_not_yet_created(tmp_path):
    project, projects = _generated_project_in_a_repo(tmp_path)

    found = foreign_plugins(project, projects)

    assert [(p.name, p.user) for p in found] == [("repo-plugin", False)]
    assert not project.exists()


def test_a_generated_projects_own_plugin_is_fine(tmp_path):
    project, projects = _generated_project_in_a_repo(tmp_path)
    _plugin(project / ".agents" / "plugins", "own")

    assert [p.name for p in foreign_plugins(project, projects)] == ["repo-plugin"]


def test_an_existing_folder_keeps_its_repos_plugins(tmp_path):
    project, _ = _generated_project_in_a_repo(tmp_path)

    assert foreign_plugins(project, tmp_path / "elsewhere") == []


def test_the_refusal_names_each_plugin_and_where_it_is_from(tmp_path, user_plugins_dir):
    path = _plugin(user_plugins_dir, "mine")
    project, projects = _generated_project_in_a_repo(tmp_path)

    text = refusal(foreign_plugins(project, projects))

    # The SDK may spell the folder differently on Windows (case, short
    # names), so the shown path is compared as a folder, not as text.
    lines = [line for line in text.splitlines() if line.startswith("  - mine: ")]
    assert len(lines) == 1, text
    assert lines[0].endswith(" (from your user folder)"), text
    shown = lines[0].removeprefix("  - mine: ").removesuffix(" (from your user folder)")
    assert os.path.samefile(shown, path), text
    assert "repo-plugin:" in text and "(from a repository above the project)" in text
    assert "certo skills add" in text


def test_the_check_finds_what_a_real_conversation_would_load(tmp_path, user_plugins_dir):
    # Guards against SDK drift: the plugin the check reports is one the SDK
    # really merges into a conversation.
    from openhands.sdk import Conversation

    from certo.agent import build_agent

    _plugin(user_plugins_dir, "mine", skill="plugin-skill")
    workspace = tmp_path / "w"
    workspace.mkdir()
    cfg = _cfg(model="anthropic/claude-haiku-4-5", workspace=str(workspace))
    conversation = Conversation(agent=build_agent(cfg), workspace=str(workspace), visualizer=None)

    conversation.send_message("hello")  # loads plugins; no model call

    assert [p.name for p in foreign_plugins(workspace, tmp_path)] == ["mine"]
    skills = {s.name for s in conversation.agent.agent_context.skills}
    assert "plugin-skill" in skills


def test_the_cli_refuses_before_creating_the_project(monkeypatch, tmp_path, capsys):
    project, projects = _generated_project_in_a_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda: _cfg(projects_dir=str(projects)))
    monkeypatch.setattr(cli, "run_task", lambda *a, **k: pytest.fail("run_task was called"))

    assert cli.main(["hi", "--project", "demo"]) == 1

    err = capsys.readouterr().err
    assert "Error: OpenHands plugins would be loaded into this run" in err
    assert "repo-plugin" in err
    assert not project.exists()


def test_a_docker_run_is_not_checked(monkeypatch, tmp_path, user_plugins_dir, capsys):
    _plugin(user_plugins_dir, "mine")
    called = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda: _cfg(execution="docker"))

    def fake_run_task(*_args, **_kwargs):
        called.append(True)
        raise RuntimeError("stop here")  # the CLI reports it; the run was reached

    monkeypatch.setattr(cli, "run_task", fake_run_task)

    cli.main(["hi"])

    assert called == [True]
    assert "OpenHands plugins" not in capsys.readouterr().err


def test_the_server_refuses_with_a_config_error(monkeypatch, tmp_path):
    project, projects = _generated_project_in_a_repo(tmp_path)
    monkeypatch.setattr(server, "load_config", lambda: _cfg(projects_dir=str(projects)))

    with pytest.raises(ConfigError, match="repo-plugin"):
        server._resolve_cfg(execution=None, project="demo", agents_md=None)
    assert not project.exists()
