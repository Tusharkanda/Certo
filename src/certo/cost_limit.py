"""Keep a run under `CERTO_MAX_TASK_COST`.

The time budget has a watcher (deadline.py); this is the same for money.
While a `conversation.run()` goes, `pause_at_cost_limit` reads the
conversation's running cost every few seconds, from the SDK's own metrics,
and pauses the conversation once the cost reaches the limit
(`conversation.pause()`, which takes effect between agent steps). The
model call under way is already paid for, so it is let finish: a run can
end a little over the limit, by the calls made since the last reading
(live, a $0.004 limit on Haiku ended at $0.0065).

The limit covers the whole task: what was spent before this conversation
(independent tests, earlier escalation rungs) counts. A resumed
conversation starts from what it has already spent, so `--resume` gets a
fresh limit, as it gets a fresh time budget. A model with no known price
costs 0 here, as everywhere in Certo.
"""

from __future__ import annotations

import threading
import weakref
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

# How often the running cost is read, in seconds.
REFRESH_SECONDS = 2.0


def conversation_cost(conversation: Any) -> float:
    """What the conversation's models have cost so far, in USD; 0 when it
    can't be read (a remote conversation, or no known price)."""
    try:
        metrics = conversation.conversation_stats.usage_to_metrics.values()
        return sum(float(m.accumulated_cost or 0) for m in metrics)
    except Exception:  # noqa: BLE001 - unknown cost counts as 0
        return 0.0


@dataclass
class CostLimit:
    limit: float
    spent_before: float
    start: float  # the conversation's own cost when the limit was set
    announced: bool = False

    def spent(self, conversation: Any) -> float:
        return self.spent_before + conversation_cost(conversation) - self.start

    def reached(self, conversation: Any) -> bool:
        return self.spent(conversation) >= self.limit


_limits: weakref.WeakKeyDictionary[Any, CostLimit] = weakref.WeakKeyDictionary()


def set_cost_limit(conversation: Any, limit: float | None, spent_before: float = 0.0) -> None:
    """Give `conversation` a cost limit in USD (None: no limit), counting
    `spent_before` as already spent."""
    if limit is None:
        _limits.pop(conversation, None)
        return
    _limits[conversation] = CostLimit(limit, spent_before, conversation_cost(conversation))


def cost_limit(conversation: Any) -> CostLimit | None:
    return _limits.get(conversation)


def cost_limit_reached(conversation: Any) -> bool:
    found = _limits.get(conversation)
    return found is not None and found.reached(conversation)


@contextmanager
def pause_at_cost_limit(conversation: Any) -> Iterator[None]:
    """While the block runs, pause `conversation` once its cost limit is
    reached. No-op for a conversation with no limit."""
    found = _limits.get(conversation)
    if found is None:
        yield
        return
    stop = threading.Event()

    def watch() -> None:
        while not stop.wait(REFRESH_SECONDS):
            if found.reached(conversation):
                conversation.pause()
                return

    watcher = threading.Thread(target=watch, name="certo-cost-limit", daemon=True)
    watcher.start()
    try:
        yield
    finally:
        stop.set()
        watcher.join()
