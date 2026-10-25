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
