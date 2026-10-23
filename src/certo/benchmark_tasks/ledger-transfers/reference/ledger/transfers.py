"""Transfers between your own accounts: money that moved, not money spent
or earned."""

from __future__ import annotations

from collections.abc import Iterable

from .models import Transaction

MAX_DAYS = 3


def _is_pair(outgoing: Transaction, incoming: Transaction) -> bool:
    days = (incoming.date - outgoing.date).days
    return (
        outgoing.account != incoming.account
        and incoming.amount == -outgoing.amount
        and 0 <= days <= MAX_DAYS
    )


def find_transfers(
    transactions: Iterable[Transaction],
) -> list[tuple[Transaction, Transaction]]:
    """(outgoing, incoming) pairs: different accounts, the same amount and
    currency with opposite signs, the incoming one 0 to 3 days after the
    outgoing one. Each transaction is in at most one pair. Outgoing
    transactions are matched earliest first, each with the earliest free
    incoming match; ties keep the given order."""
    items = list(transactions)
    order = sorted(range(len(items)), key=lambda i: (items[i].date, i))
    outgoing = [i for i in order if items[i].amount.amount < 0]
    incoming = [i for i in order if items[i].amount.amount > 0]
    taken: set[int] = set()
    pairs = []
    for out in outgoing:
        for inc in incoming:
            if inc not in taken and _is_pair(items[out], items[inc]):
                taken.add(inc)
                pairs.append((items[out], items[inc]))
                break
    return pairs
