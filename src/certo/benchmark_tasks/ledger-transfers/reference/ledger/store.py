"""Keep imported transactions in a JSON Lines file, one per line."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from pathlib import Path

from .models import Transaction
from .money import Money


class StoreError(ValueError):
    """A store line that isn't a transaction."""


def to_record(transaction: Transaction) -> dict:
    return {
        "date": transaction.date.isoformat(),
        "description": transaction.description,
        "amount": str(transaction.amount.amount),
        "currency": transaction.amount.currency,
        "account": transaction.account,
        "category": transaction.category,
    }


def from_record(record: dict) -> Transaction:
    try:
        return Transaction(
            date=date.fromisoformat(record["date"]),
            description=record["description"],
            amount=Money(Decimal(record["amount"]), record["currency"]),
            account=record["account"],
            category=record.get("category"),
        )
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise StoreError(f"not a transaction: {record!r} ({exc})") from None


def load(path: str | Path) -> list[Transaction]:
    """Every stored transaction, in file order; none when the file doesn't
    exist yet."""
    path = Path(path)
    if not path.exists():
        return []
    result = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StoreError(f"{path}:{number}: {exc}") from None
        result.append(from_record(record))
    return result


def save(path: str | Path, transactions: Iterable[Transaction]) -> None:
    """Write every transaction, replacing the file (via a temporary file,
    so a crash never leaves half a store)."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for transaction in transactions:
            handle.write(json.dumps(to_record(transaction), sort_keys=True) + "\n")
    tmp.replace(path)


def merge(existing: list[Transaction], new: Iterable[Transaction]) -> list[Transaction]:
    """`existing` plus the transactions of `new` it doesn't have yet (same
    date, description, amount and account), sorted by date. Importing the
    same statement twice adds nothing."""
    seen = {t.key() for t in existing}
    result = list(existing)
    for transaction in new:
        if transaction.key() not in seen:
            seen.add(transaction.key())
            result.append(transaction)
    return sorted(result, key=lambda t: t.date)
