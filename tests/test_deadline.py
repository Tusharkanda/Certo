import threading
import time

import pytest
from openhands.tools.terminal.timeout_policy import (
    RUNTIME_IDLE_TIMEOUT_SECONDS_ENV as ENV,
)
from openhands.tools.terminal.timeout_policy import (
    foreground_timeout_rejection_for,
    get_max_foreground_timeout_seconds,
)

from certo import deadline as dl


class FakeConversation:
    def __init__(self) -> None:
        self.paused = threading.Event()

    def pause(self) -> None:
        self.paused.set()


@pytest.fixture(autouse=True)
def no_user_setting(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)


def test_terminal_timeout_capped_at_time_left_then_restored():
    with dl.stop_at_deadline(FakeConversation(), time.monotonic() + 600):
        cap = get_max_foreground_timeout_seconds()
        assert 595 <= cap <= 601
        # The SDK refuses a longer foreground timeout, accepts a shorter one.
        assert foreground_timeout_rejection_for(command="sleep 1", is_input=False, timeout=10_000)
        assert not foreground_timeout_rejection_for(command="sleep 1", is_input=False, timeout=60)
    assert get_max_foreground_timeout_seconds() is None


def test_a_lower_user_setting_is_kept(monkeypatch):
    monkeypatch.setenv(ENV, "100")
    with dl.stop_at_deadline(FakeConversation(), time.monotonic() + 600):
        assert get_max_foreground_timeout_seconds() == pytest.approx(90)
    assert get_max_foreground_timeout_seconds() == pytest.approx(90)


def test_the_conversation_is_paused_at_the_deadline():
    conversation = FakeConversation()
    with dl.stop_at_deadline(conversation, time.monotonic() + 0.2):
        assert conversation.paused.wait(5)


def test_not_paused_when_the_run_ends_first():
    conversation = FakeConversation()
    with dl.stop_at_deadline(conversation, time.monotonic() + 0.5):
        pass
    time.sleep(0.7)
    assert not conversation.paused.is_set()


def test_the_cap_follows_the_time_left(monkeypatch):
    monkeypatch.setattr(dl, "REFRESH_SECONDS", 0.05)
    with dl.stop_at_deadline(FakeConversation(), time.monotonic() + 30):
        first = get_max_foreground_timeout_seconds()
        time.sleep(1.2)
        assert get_max_foreground_timeout_seconds() < first


def test_two_runs_at_once_use_the_nearer_deadline():
    with dl.stop_at_deadline(FakeConversation(), time.monotonic() + 1000):
        with dl.stop_at_deadline(FakeConversation(), time.monotonic() + 100):
            assert get_max_foreground_timeout_seconds() <= 101
        assert get_max_foreground_timeout_seconds() > 900


def test_no_deadline_changes_nothing():
    conversation = FakeConversation()
    with dl.stop_at_deadline(conversation, float("inf")):
        assert get_max_foreground_timeout_seconds() is None
    assert not conversation.paused.is_set()


# --- The model's per-call timeout -----------------------------------------


class ModelConversation(FakeConversation):
    """A fake conversation with a real SDK LLM (no call is made)."""

    def __init__(self, timeout=1200) -> None:
        from types import SimpleNamespace

        from openhands.sdk import LLM

        super().__init__()
        self.agent = SimpleNamespace(llm=LLM(usage_id="t", model="openai/gpt-4o", timeout=timeout))


def test_the_model_timeout_is_capped_at_time_left_then_restored():
    conversation = ModelConversation(timeout=1200)
    llm = conversation.agent.llm
    with dl.stop_at_deadline(conversation, time.monotonic() + 600):
        assert 600 <= llm.timeout <= 602
    assert llm.timeout == 1200


@pytest.mark.parametrize(("own", "expected"), [(60, 60), (None, 602)])
def test_a_shorter_model_timeout_is_kept_and_none_is_capped(own, expected):
    conversation = ModelConversation(timeout=own)
    with dl.stop_at_deadline(conversation, time.monotonic() + 600):
        assert conversation.agent.llm.timeout <= expected
        assert conversation.agent.llm.timeout >= min(expected, 600)
    assert conversation.agent.llm.timeout == own


def test_the_model_cap_follows_the_time_left(monkeypatch):
    monkeypatch.setattr(dl, "REFRESH_SECONDS", 0.05)
    conversation = ModelConversation()
    with dl.stop_at_deadline(conversation, time.monotonic() + 30):
        first = conversation.agent.llm.timeout
        time.sleep(1.2)
        assert conversation.agent.llm.timeout < first


def test_retries_stop_after_the_deadline():
    from litellm.exceptions import Timeout

    conversation = ModelConversation()
    llm = conversation.agent.llm
    attempts = []

    @llm._make_retry_decorator()
    def call():
        attempts.append(1)
        raise Timeout("timed out", model="gpt-4o", llm_provider="openai")

    with dl.stop_at_deadline(conversation, time.monotonic() + 0.1):
        assert conversation.paused.wait(5)
        assert llm.timeout == 1
        started = time.monotonic()
        with pytest.raises(Timeout):
            call()
    assert attempts == [1]  # no retry, so no 8-second wait either
    assert time.monotonic() - started < 5
    assert llm.timeout == 1200 and llm.retry_listener is None
