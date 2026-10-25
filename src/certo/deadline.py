"""Keep one `conversation.run()` inside the task's time budget.

The runner checks the budget only between runs, and a run can last long
after the deadline: one terminal command may ask for any timeout (a
0.1.23 baseline run waited 10,000 seconds). While a run goes, `stop_at_deadline`:

- caps every terminal command's timeout at the time left, through the
  SDK's own foreground-timeout cap (`OH_RUNTIME_IDLE_TIMEOUT_SECONDS`,
  read from the environment on every command; a longer timeout is
  refused with a message telling the agent to use a shorter one);
- pauses the conversation at the deadline (`conversation.pause()`, which
  takes effect between agent steps).

The cap is process-wide, so with several runs at once (server mode) it
follows the run closest to its deadline.
"""

from __future__ import annotations

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


@contextmanager
def stop_at_deadline(conversation: Any, deadline: float) -> Iterator[None]:
    """While the block runs: terminal timeouts are capped at the time left
    before `deadline` (a `time.monotonic()` timestamp), and `conversation`
    is paused when it passes. No-op for an infinite deadline."""
    global _user_setting
    if deadline == float("inf"):
        yield
        return
    with _lock:
        if not _deadlines:
            _user_setting = os.environ.get(RUNTIME_IDLE_TIMEOUT_SECONDS_ENV)
        _deadlines.append(deadline)
    _refresh_cap()
    stop = threading.Event()

    def watch() -> None:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                conversation.pause()
                return
            if stop.wait(min(REFRESH_SECONDS, left)):
                return
            _refresh_cap()

    watcher = threading.Thread(target=watch, name="certo-deadline", daemon=True)
    watcher.start()
    try:
        yield
    finally:
        stop.set()
        watcher.join()
        with _lock:
            _deadlines.remove(deadline)
        _refresh_cap()
