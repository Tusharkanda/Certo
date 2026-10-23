import pytest

from ledger.categorize import Rule, RuleError, categorize, category_for, parse_rules
from tests.helpers import tx


def test_parse_rules_skips_comments_and_blank_lines():
    rules = parse_rules(["# rules", "", "supermarket => groceries  # food", "rent=>housing"])
    assert rules == [Rule("supermarket", "groceries"), Rule("rent", "housing")]


@pytest.mark.parametrize("line", ["supermarket", "=> groceries", "supermarket =>"])
def test_parse_rules_rejects_bad_lines(line):
    with pytest.raises(RuleError, match="line 1"):
        parse_rules([line])


def test_first_matching_rule_wins_ignoring_case():
    rules = [Rule("fresh", "groceries"), Rule("supermarket", "shopping")]
    assert category_for("SUPERMARKET FRESH", rules) == "groceries"
    assert category_for("Bakery", rules) is None


def test_categorize_keeps_an_existing_category():
    rules = [Rule("fresh", "groceries")]
    done = categorize([tx("Fresh", -10, category="gifts"), tx("Fresh", -5)], rules)
    assert [t.category for t in done] == ["gifts", "groceries"]
