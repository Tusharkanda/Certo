"""Give transactions a category from a list of rules.

A rules file has one rule per line, `pattern => category`, and `#`
comments. A transaction gets the category of the first rule whose pattern
appears in its description, ignoring case. A transaction that already has
a category keeps it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .models import Transaction


class RuleError(ValueError):
    """A rules file line that isn't `pattern => category`."""


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str

    def matches(self, description: str) -> bool:
        return self.pattern.casefold() in description.casefold()


def parse_rules(lines: Iterable[str]) -> list[Rule]:
    rules = []
    for number, line in enumerate(lines, start=1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        pattern, sep, category = line.partition("=>")
        if not sep or not pattern.strip() or not category.strip():
            raise RuleError(f"line {number}: expected 'pattern => category', got {line!r}")
        rules.append(Rule(pattern.strip(), category.strip()))
    return rules


def load_rules(path: str | Path) -> list[Rule]:
    return parse_rules(Path(path).read_text(encoding="utf-8").splitlines())


def category_for(description: str, rules: list[Rule]) -> str | None:
    for rule in rules:
        if rule.matches(description):
            return rule.category
    return None


def categorize(transactions: Iterable[Transaction], rules: list[Rule]) -> list[Transaction]:
    """The same transactions, in the same order, with a category where a
    rule matches and none was set."""
    result = []
    for transaction in transactions:
        if transaction.category is None:
            transaction = transaction.with_category(category_for(transaction.description, rules))
        result.append(transaction)
    return result
