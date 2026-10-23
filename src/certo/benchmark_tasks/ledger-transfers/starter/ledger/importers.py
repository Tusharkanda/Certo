"""Read the CSV files two banks export.

Alpha Bank: comma-separated, a header line `Date,Description,Amount,Currency`,
dates as `31/12/2025` (day first), signed amounts (`-12.50` is money out).

Beta Bank: semicolon-separated, a header line `Booking date;Text;Amount`,
ISO dates (`2025-12-31`), every amount in the account's currency, and
money out written in accounting style, in parentheses: `(12.50)`.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

from .models import Transaction
from .money import Money, MoneyError, parse_amount

ALPHA_HEADER = ["Date", "Description", "Amount", "Currency"]
BETA_HEADER = ["Booking date", "Text", "Amount"]


class ImportError_(ValueError):
    """A file that isn't a statement we can read, with the line at fault."""


def _alpha_date(text: str) -> date:
    return datetime.strptime(text.strip(), "%d/%m/%Y").date()


def _beta_date(text: str) -> date:
    return date.fromisoformat(text.strip())


def read_alpha(lines: Iterable[str], account: str) -> list[Transaction]:
    reader = csv.reader(lines)
    header = next(reader, None)
    if header != ALPHA_HEADER:
        raise ImportError_(f"not an Alpha Bank file: header is {header}")
    result = []
    for number, row in enumerate(reader, start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != 4:
            raise ImportError_(f"line {number}: expected 4 fields, got {len(row)}")
        try:
            result.append(
                Transaction(
                    date=_alpha_date(row[0]),
                    description=row[1].strip(),
                    amount=Money(parse_amount(row[2]), row[3].strip().upper()),
                    account=account,
                )
            )
        except (ValueError, MoneyError) as exc:
            raise ImportError_(f"line {number}: {exc}") from None
    return result


def read_beta(lines: Iterable[str], account: str, currency: str = "EUR") -> list[Transaction]:
    reader = csv.reader(lines, delimiter=";")
    header = next(reader, None)
    if header != BETA_HEADER:
        raise ImportError_(f"not a Beta Bank file: header is {header}")
    result = []
    for number, row in enumerate(reader, start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != 3:
            raise ImportError_(f"line {number}: expected 3 fields, got {len(row)}")
        try:
            result.append(
                Transaction(
                    date=_beta_date(row[0]),
                    description=row[1].strip(),
                    amount=Money(parse_amount(row[2]), currency),
                    account=account,
                )
            )
        except (ValueError, MoneyError) as exc:
            raise ImportError_(f"line {number}: {exc}") from None
    return result


def detect(first_line: str) -> str:
    """ "alpha" or "beta", from a file's header line."""
    header = first_line.strip().lstrip("﻿")
    if header == ",".join(ALPHA_HEADER):
        return "alpha"
    if header == ";".join(BETA_HEADER):
        return "beta"
    raise ImportError_(f"unknown statement format: {header!r}")


def import_file(path: str | Path, account: str, currency: str = "EUR") -> list[Transaction]:
    """Every transaction in one exported file, in file order. `currency` is
    used only for Beta Bank files, which don't name one."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines:
        raise ImportError_(f"{path} is empty")
    if detect(lines[0]) == "alpha":
        return read_alpha(lines, account)
    return read_beta(lines, account, currency)
