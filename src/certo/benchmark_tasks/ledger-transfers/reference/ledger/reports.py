"""Totals per month and category, balances, and their text tables."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .models import Transaction
from .money import Money
from .transfers import find_transfers

UNCATEGORIZED = "uncategorized"


def monthly_totals(
    transactions: Iterable[Transaction],
) -> dict[tuple[int, int], dict[str, Money]]:
    """For each (year, month), the total amount per category. Money out is
    negative, money in positive; a transaction with no category counts
    under "uncategorized". Months and categories with no transactions are
    left out, and so is every transaction that is part of a transfer
    between your own accounts (`transfers.py`)."""
    items = list(transactions)
    # By identity: two equal transactions can be one transfer and one purchase.
    in_transfers = {id(t) for pair in find_transfers(items) for t in pair}
    totals: dict[tuple[int, int], dict[str, Money]] = defaultdict(dict)
    for transaction in items:
        if id(transaction) in in_transfers:
            continue
        category = transaction.category or UNCATEGORIZED
        month = totals[transaction.month]
        if category in month:
            month[category] = month[category] + transaction.amount
        else:
            month[category] = transaction.amount
    return {month: dict(categories) for month, categories in sorted(totals.items())}


def balances(transactions: Iterable[Transaction]) -> dict[tuple[str, str], Money]:
    """The sum of every transaction per (account, currency)."""
    result: dict[tuple[str, str], Money] = {}
    for transaction in transactions:
        key = (transaction.account, transaction.amount.currency)
        result[key] = result[key] + transaction.amount if key in result else transaction.amount
    return dict(sorted(result.items()))


def format_month(month: tuple[int, int], categories: dict[str, Money]) -> str:
    """One month as a table: categories by name, then the net total per
    currency."""
    year, number = month
    lines = [f"{year}-{number:02d}"]
    width = max((len(name) for name in categories), default=0)
    for name in sorted(categories):
        lines.append(f"  {name:<{width}}  {categories[name].format():>18}")
    nets: dict[str, Money] = {}
    for amount in categories.values():
        nets[amount.currency] = (
            nets[amount.currency] + amount if amount.currency in nets else amount
        )
    for currency in sorted(nets):
        lines.append(f"  {'net':<{width}}  {nets[currency].format():>18}")
    return "\n".join(lines)


def format_report(transactions: Iterable[Transaction], month: tuple[int, int] | None = None) -> str:
    totals = monthly_totals(transactions)
    if month is not None:
        totals = {month: totals[month]} if month in totals else {}
    if not totals:
        return "No transactions."
    return "\n\n".join(format_month(m, c) for m, c in totals.items())
