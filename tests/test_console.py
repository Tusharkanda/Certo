import logging

from openhands.sdk import Message, TextContent
from openhands.sdk.conversation.visualizer import DefaultConversationVisualizer
from openhands.sdk.event import MessageEvent, SystemPromptEvent
from openhands.sdk.event.conversation_error import ConversationErrorEvent

from certo.config import Config
from certo.console import QuietVisualizer, quiet_sdk_logs, visualizer_for


def _cfg(**overrides) -> Config:
    base = {
        "model": "openai/gpt-4o",
        "api_key": "key",
        "base_url": None,
        "workspace": ".",
        "max_iterations": 10,
        "confirm_mode": "never",
        "execution": "local",
    }
    base.update(overrides)
    return Config(**base)


def _user(text: str) -> MessageEvent:
    return MessageEvent(
        source="user", llm_message=Message(role="user", content=[TextContent(text=text)])
    )


def test_the_system_prompt_is_one_line(capsys):
    prompt = "\n".join(f"rule {i}" for i in range(500))
    QuietVisualizer().on_event(SystemPromptEvent(system_prompt=TextContent(text=prompt), tools=[]))

    out = capsys.readouterr().out
    assert out.startswith("System prompt: ")
    assert "lines (--verbose shows it)" in out
    assert "rule 7" not in out
    assert len(out.splitlines()) == 1


def test_the_task_is_its_title_and_the_next_user_messages_are_shown_in_full(capsys):
    visualizer = QuietVisualizer()
    visualizer.on_event(_user("# A Wordle game\n\nBuild it.\n" + "skill line\n" * 240))
    first = capsys.readouterr().out
    assert first.startswith("Task: A Wordle game (")
    assert "skill line" not in first

    # A later user message is Certo's own follow-up (failing checks, say):
    # the SDK's visualizer shows it whole.
    visualizer.on_event(_user("Automated verification ran: pytest failed"))
    assert "Automated verification ran: pytest failed" in capsys.readouterr().out


def test_a_conversation_error_is_left_to_certo_with_no_sdk_warning(capsys, caplog):
    # Live 2026-10-22: a rung whose key was rejected printed the SDK's
    # "not registered in EVENT_VISUALIZATION_CONFIG" warning before
    # Certo's own line about the failure.
    with caplog.at_level(logging.WARNING):
        QuietVisualizer().on_event(
            ConversationErrorEvent(source="environment", code="LLMError", detail="rejected")
        )
    assert capsys.readouterr().out == ""
    assert "EVENT_VISUALIZATION_CONFIG" not in caplog.text


def test_verbose_uses_the_sdk_visualizer_and_the_default_a_fresh_quiet_one():
    assert visualizer_for(_cfg(verbose=True)) is DefaultConversationVisualizer
    first, second = visualizer_for(_cfg()), visualizer_for(_cfg())
    assert isinstance(first, QuietVisualizer)
    assert first is not second  # each conversation shows its own task line


def test_sdk_info_logs_are_hidden_unless_verbose_or_log_level(monkeypatch):
    sdk = logging.getLogger("openhands")
    monkeypatch.setattr(sdk, "level", logging.NOTSET)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    quiet_sdk_logs(_cfg(verbose=True))
    assert sdk.level == logging.NOTSET
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    quiet_sdk_logs(_cfg())
    assert sdk.level == logging.NOTSET
    monkeypatch.delenv("LOG_LEVEL")
    quiet_sdk_logs(_cfg())
    assert sdk.level == logging.WARNING
