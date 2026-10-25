"""Keep one `conversation.run()` inside the task's time budget.

The runner checks the budget only between runs, and a run can last long
after the deadline: one terminal command may ask for any timeout (a
0.1.23 baseline run waited 10,000 seconds). While a run goes, `stop_at_deadline`:

- caps every terminal command's timeout at the time left, through the
  SDK's own foreground-timeout cap (`OH_RUNTIME_IDLE_TIMEOUT_SECONDS`,
  read from the environment on every command; a longer timeout is
  refused with a message telling the agent to use a shorter one);
- caps the model's per-call timeout at the time left (the SDK's `LLM`
  reads `timeout` on every attempt), so a call can't wait much past the
  deadline, and after the deadline stops the SDK's retries of a failed
  call (its `retry_listener` runs before each retry; raising there ends
  them). The call already under way ends with an error, which the runner
  treats as the budget running out (runner.py);
- pauses the conversation at the deadline (`conversation.pause()`, which
  takes effect between agent steps).

The cap is process-wide, so with several runs at once (server mode) it
follows the run closest to its deadline.
"""

from __future__ import annotations

import math
import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from openhands.tools.terminal.timeout_policy import (
    MAX_FOREGROUND_TIMEOUT_RATIO,
    RUNTIME_IDLE_TIMEOUT_SECONDS_ENV,
)

# How often the cap follows the shrinking time left, in seconds.
REFRESH_SECONDS = 5.0

_lock = threading.Lock()
_deadlines: list[float] = []
_user_setting: str | None = None


def _idle_setting(seconds_left: float) -> str:
    """The SDK setting whose cap (90% of it) is `seconds_left`."""
    return f"{max(seconds_left, 1.0) / MAX_FOREGROUND_TIMEOUT_RATIO:.0f}"


def _refresh_cap() -> None:
    """Point the SDK's cap at the nearest deadline, never above a value the
    user set; with no run going, put the user's value back."""
    with _lock:
        if not _deadlines:
            if _user_setting is None:
                os.environ.pop(RUNTIME_IDLE_TIMEOUT_SECONDS_ENV, None)
            else:
                os.environ[RUNTIME_IDLE_TIMEOUT_SECONDS_ENV] = _user_setting
            return
        setting = _idle_setting(min(_deadlines) - time.monotonic())
        if _user_setting is not None:
            try:
                if float(_user_setting) < float(setting):
                    setting = _user_setting
            except ValueError:
                pass
        os.environ[RUNTIME_IDLE_TIMEOUT_SECONDS_ENV] = setting


class _ModelCap:
    """Caps the conversation's model at the time left, and puts its own
    settings back afterwards. The model is read again on every refresh:
    `--auto-model` can switch it during a run."""

    def __init__(self, conversation: Any) -> None:
        self.conversation = conversation
        self.saved: dict[int, tuple[Any, Any, Any]] = {}

    def _llm(self) -> Any:
        try:
            llm = self.conversation.agent.llm
        except Exception:  # noqa: BLE001 - a fake or remote conversation: nothing to cap
            return None
        if id(llm) not in self.saved:
            self.saved[id(llm)] = (llm, llm.timeout, llm.retry_listener)
        return llm

    def refresh(self, seconds_left: float) -> None:
        llm = self._llm()
        if llm is None:
            return
        # One second over, so a call cut short ends after the deadline.
        cap = math.ceil(max(seconds_left, 0)) + 1
        own = self.saved[id(llm)][1]
        llm.timeout = cap if own is None else min(own, cap)

    def stop_retries(self) -> None:
        llm = self._llm()
        if llm is None:
            return
        llm.timeout = 1

        def no_retry(_attempt: int, _retries: int, error: BaseException | None) -> None:
            if error is not None:
                raise error

        llm.retry_listener = no_retry

    def restore(self) -> None:
        for llm, timeout, listener in self.saved.values():
            llm.timeout = timeout
            llm.retry_listener = listener


@contextmanager
def stop_at_deadline(conversation: Any, deadline: float) -> Iterator[None]:
    """While the block runs: terminal timeouts and the model's per-call
    timeout are capped at the time left before `deadline` (a
    `time.monotonic()` timestamp), and when it passes `conversation` is
    paused and the model's retries stop. No-op for an infinite deadline."""
    global _user_setting
    if deadline == float("inf"):
        yield
        return
    with _lock:
        if not _deadlines:
            _user_setting = os.environ.get(RUNTIME_IDLE_TIMEOUT_SECONDS_ENV)
        _deadlines.append(deadline)
    _refresh_cap()
    model = _ModelCap(conversation)
    model.refresh(deadline - time.monotonic())
    stop = threading.Event()

    def watch() -> None:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                model.stop_retries()
                conversation.pause()
                return
            if stop.wait(min(REFRESH_SECONDS, left)):
                return
            _refresh_cap()
            model.refresh(deadline - time.monotonic())

    watcher = threading.Thread(target=watch, name="certo-deadline", daemon=True)
    watcher.start()
    try:
        yield
    finally:
        stop.set()
        watcher.join()
        model.restore()
        with _lock:
            _deadlines.remove(deadline)
        _refresh_cap()
