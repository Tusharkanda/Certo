"""The run banner: pure formatting from a Config, no LLM."""

from __future__ import annotations

from types import SimpleNamespace

from certo import __version__
from certo.banner import format_banner
from certo.config import Config


def _cfg(**overrides) -> Config:
    base = {
        "model": "openai/gpt-4o",
        "api_key": "key",
        "base_url": None,
        "workspace": "/tmp/work",
        "max_iterations": 100,
        "confirm_mode": "never",
        "execution": "local",
    }
    base.update(overrides)
    return Config(**base)


def _ladder(*names):
    return SimpleNamespace(rungs=[SimpleNamespace(name=n) for n in names])


def test_the_banner_names_the_version_model_folder_and_limits(tmp_path):
    text = "\n".join(format_banner(_cfg(workspace=str(tmp_path)), project="todo"))

    assert f"Certo {__version__}" in text
    assert "Model    openai/gpt-4o" in text
    assert f"Folder   {tmp_path} (project todo)" in text
    assert "Runs on  this computer" in text
    assert "Checks   on, up to 2 fix attempts" in text
    assert "Limits   30 min · 100 steps" in text
    assert "  Mode " not in text


def test_a_local_server_shows_host_and_port_but_never_a_password():
    lines = format_banner(
        _cfg(model="ollama/qwen3.8:27b", base_url="http://me:secret@gpu-box:11434/v1")
    )

    assert "  Model    ollama/qwen3.8:27b at gpu-box:11434" in lines
    assert "secret" not in "\n".join(lines)


def test_the_api_key_is_never_shown():
    assert "sk-very-secret" not in "\n".join(format_banner(_cfg(api_key="sk-very-secret")))


def test_escalation_shows_the_ladder_and_the_cost_cap():
    text = "\n".join(
        format_banner(
            _cfg(model_selection="escalate", max_task_cost=0.5),
            ladder=_ladder("qwen3.8-27b-local", "claude-haiku-5-5"),
        )
    )

    assert "Model    escalate: qwen3.8-27b-local → claude-haiku-5-5" in text
    assert "Limits   30 min · 100 steps · $0.50" in text


def test_auto_model_docker_no_checks_and_modes():
    text = "\n".join(
        format_banner(
            _cfg(
                model_selection="auto",
                execution="docker",
                docker_image="python:3.12",
                verify_tests="never",
                max_task_seconds=90,
                interactive=True,
                confirm_mode="always",
            )
        )
    )

    assert "Model    auto: picked from the model files for this task" in text
    assert "Runs on  Docker (python:3.12)" in text
    assert "Checks   off (CERTO_VERIFY_TESTS=never)" in text
    assert "Limits   1m 30s · 100 steps" in text
    assert "Mode     interactive: the agent may ask you questions; confirm:" in text
