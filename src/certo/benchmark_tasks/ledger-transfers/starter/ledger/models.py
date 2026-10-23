"""The transaction: one line of a bank statement."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from .money import Money


@dataclass(frozen=True)
class Transaction:
    date: date
    description: str
    amount: Money  # negative: money that left the account
    account: str  # your name for the account, e.g. "checking"
    category: str | None = None  # None: not categorized yet

    @property
    def is_expense(self) -> bool:
        return self.amount.is_negative

    @property
    def month(self) -> tuple[int, int]:
        return (self.date.year, self.date.month)

    def with_category(self, category: str | None) -> Transaction:
        return replace(self, category=category)

    def key(self) -> tuple:
        """What makes two imports of the same statement line the same."""
        return (self.date, self.description, self.amount, self.account)
