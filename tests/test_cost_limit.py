"""cost_limit.py: the running cost and the watcher that pauses a run at
CERTO_MAX_TASK_COST. No model, no network."""

from __future__ import annotations

import threading
from types import SimpleNamespace

from certo import cost_limit
from certo.cost_limit import (
    conversation_cost,
    cost_limit_reached,
    pause_at_cost_limit,
    set_cost_limit,
)


class _Conversation:
    def __init__(self, *costs: float) -> None:
        self.conversation_stats = SimpleNamespace(
            usage_to_metrics={
                f"m{i}": SimpleNamespace(accumulated_cost=c) for i, c in enumerate(costs)
            }
        )
        self.paused = threading.Event()

    def spend(self, amount: float) -> None:
        self.conversation_stats.usage_to_metrics["m0"].accumulated_cost += amount

    def pause(self) -> None:
        self.paused.set()


def test_the_cost_adds_every_model_and_unknown_is_zero():
    assert conversation_cost(_Conversation(0.25, 0.5)) == 0.75
    assert conversation_cost(object()) == 0.0  # a remote conversation: no stats


def test_the_limit_counts_what_was_spent_before():
    conversation = _Conversation(0.0)
    set_cost_limit(conversation, 1.0, spent_before=0.75)
    assert not cost_limit_reached(conversation)

    conversation.spend(0.25)

    assert cost_limit_reached(conversation)


def test_a_resumed_conversation_starts_from_what_it_already_spent():
    conversation = _Conversation(5.0)  # the earlier session's cost
    set_cost_limit(conversation, 1.0)

    assert not cost_limit_reached(conversation)
    conversation.spend(1.0)
    assert cost_limit_reached(conversation)


def test_no_limit_means_never_reached():
    conversation = _Conversation(100.0)
    set_cost_limit(conversation, None)

    assert not cost_limit_reached(conversation)


def test_the_watcher_pauses_the_run_once_the_limit_is_reached(monkeypatch):
    monkeypatch.setattr(cost_limit, "REFRESH_SECONDS", 0.01)
    conversation = _Conversation(0.0)
    set_cost_limit(conversation, 0.5)

    with pause_at_cost_limit(conversation):
        assert not conversation.paused.wait(0.05)
        conversation.spend(0.5)
        assert conversation.paused.wait(2)


def test_the_watcher_is_a_no_op_without_a_limit():
    conversation = _Conversation(100.0)

    with pause_at_cost_limit(conversation):
        pass

    assert not conversation.paused.is_set()
