"""skill_library.py tests: the layers a run's skills come from, what
replaces what, and how a skill fires. Real SDK loading, no network."""

from __future__ import annotations

from pathlib import Path

import pytest

from certo import skill_library as lib
from certo import third_party_skills as tps
from certo.agent import build_agent
from certo.config import load_config

KEYWORD_SKILL = """---
name: {name}
triggers:
  - snake
---
{body}
"""


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A clean user folder and current folder."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _cfg(tmp_path: Path):
    return load_config({"CERTO_LLM_MODEL": "openai/gpt-4o", "CERTO_LLM_API_KEY": "k"})


def _write(folder: Path, name: str, body: str = "Short functions.") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.md"
    path.write_text(KEYWORD_SKILL.format(name=name, body=body))
    return path


def _rows(found: lib.SkillSet, layer: str) -> dict[str, lib.SkillRow]:
    return {r.name: r for r in found.rows if r.layer == layer}


def test_official_global_and_project_layers(home):
    _write(lib.global_dir(), "my-style")
    project = home / "projects" / "demo"
    _write(lib.project_dir(project), "game-rules")

    found = lib.collect(_cfg(home), project)

    assert "testing-and-verification" in _rows(found, lib.OFFICIAL)
    assert set(_rows(found, lib.GLOBAL)) == {"my-style"}
    assert set(_rows(found, lib.PROJECT)) == {"game-rules"}
    names = {s.name for s in found.skills}
    assert {"my-style", "game-rules", "testing-and-verification"} <= names
    assert found.notices == ()


def test_a_third_party_skill_replaces_an_official_one_and_a_run_says_so(home):
    _write(lib.global_dir(), "pytest-conventions", "Mine.")

    found = lib.collect(_cfg(home), None)

    official = _rows(found, lib.OFFICIAL)["pytest-conventions"]
    assert official.replaced_by == lib.GLOBAL and not official.active
    assert [s.content.strip() for s in found.skills if s.name == "pytest-conventions"] == ["Mine."]
    assert found.notices == (
        "Certo: your global skill 'pytest-conventions' replaces the official one.",
    )


def test_a_project_skill_replaces_a_global_one(home):
    _write(lib.global_dir(), "my-style", "Global.")
    project = home / "p"
    _write(lib.project_dir(project), "my-style", "Project.")

    found = lib.collect(_cfg(home), project)

    assert _rows(found, lib.GLOBAL)["my-style"].replaced_by == lib.PROJECT
    assert [s.content.strip() for s in found.skills if s.name == "my-style"] == ["Project."]


def test_the_projects_own_skills_are_listed_and_left_to_the_sdk(home):
    project = home / "p"
    (project / ".agents" / "skills").mkdir(parents=True)
    _write(project / ".agents" / "skills", "own-rule")

    found = lib.collect(_cfg(home), project)

    assert "own-rule" in _rows(found, lib.OWN)
    assert "own-rule" not in {s.name for s in found.skills}
    assert lib.collect(_cfg(home), project, own=False).rows == tuple(
        r for r in found.rows if r.layer != lib.OWN
    )


def test_only_the_top_level_is_read_never_a_git_cache(home):
    root = lib.global_dir()
    _write(root / ".cache" / "repo", "from-cache")
    _write(root / "nested", "deep")  # a folder without SKILL.md
    (root / "README.md").write_text("not a skill")

    rows = _rows(lib.collect(_cfg(home), None), lib.GLOBAL)

    assert "from-cache" not in rows and "deep" not in rows and "README" not in rows
    assert rows["nested"].state.startswith("can't load")


def test_inline_commands_in_a_third_party_skill_are_escaped(home):
    _write(lib.global_dir(), "risky", "Run !`rm -rf /` now.")

    skill = next(s for s in lib.collect(_cfg(home), None).skills if s.name == "risky")

    assert "\\!`rm -rf /`" in skill.content


def test_a_downloaded_skill_is_off_until_enabled(home, monkeypatch):
    root = lib.global_dir()
    root.mkdir(parents=True)
    entry = tps.LockEntry(
        source="https://github.com/o/r.git",
        path="skills/dl",
        revision="a" * 40,
        requested_ref=None,
        license="MIT",
        license_files=[],
        license_notes=[],
        license_url=None,
        source_url="https://github.com/o/r/tree/x/skills/dl",
        integrity="",
    )
    (root / "dl").mkdir()
    (root / "dl" / "SKILL.md").write_text("---\nname: dl\ndescription: d\n---\nBody\n")
    entry.integrity = tps.compute_integrity(root / "dl")
    tps.write_lock(lib.lock_path(root), {"dl": entry})

    row = _rows(lib.collect(_cfg(home), None), lib.GLOBAL)["dl"]
    assert row.skill is None and row.downloaded
    assert row.state == "off (downloaded; turn it on with: certo skills enable dl --global)"

    tps.set_enabled("dl", True, install_dir=root, lock_path=lib.lock_path(root))
    assert _rows(lib.collect(_cfg(home), None), lib.GLOBAL)["dl"].active


def test_how_a_skill_fires_and_for_which_task(home):
    official = {r.name: r.skill for r in lib.collect(_cfg(home), None).rows}

    pytest_skill = official["pytest-conventions"]
    assert lib.how_it_fires(pytest_skill) == "when the task says: pytest, test, tests, unit test"
    assert lib.fires_for_task(pytest_skill, "Add pytest tests") == '"pytest" is in the task'
    assert lib.fires_for_task(pytest_skill, "Write a poem") is None
    pins = official["pin-dependencies"]
    assert lib.how_it_fires(pins).startswith("when the agent touches: pyproject.toml")
    assert lib.later_for_task(pins).startswith("if the agent touches pyproject.toml")
    assert lib.size_in_tokens(pytest_skill) > 0


def test_a_run_gets_the_global_skill(home):
    _write(lib.global_dir(), "my-style")
    cfg = _cfg(home)

    agent = build_agent(cfg)

    assert "my-style" in {s.name for s in agent.agent_context.skills}
