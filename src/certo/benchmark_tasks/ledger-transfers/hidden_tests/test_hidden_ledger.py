from datetime import date, timedelta
from decimal import Decimal

import pytest

from ledger import store
from ledger.categorize import Rule, categorize
from ledger.importers import read_beta
from ledger.models import Transaction
from ledger.money import Money, MoneyError, parse_amount
from ledger.reports import monthly_totals
from ledger.transfers import find_transfers

D = date(2025, 11, 12)


def t(amount, *, day=D, account="checking", currency="EUR", category=None, text="x"):
    return Transaction(day, text, Money(Decimal(str(amount)), currency), account, category)


# --- Bug 1: parentheses ------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "value"),
    [("(23.90)", "-23.90"), ("(1,234.50)", "-1234.50"), (" (7) ", "-7"), ("12.00", "12.00")],
)
def test_hidden_parentheses_mean_negative(text, value):
    assert parse_amount(text) == Decimal(value)


@pytest.mark.parametrize("text", ["()", "(5", "5)", "(-5)", "(+5)", "((5))", "-(5)"])
def test_hidden_bad_parentheses_are_not_amounts(text):
    with pytest.raises(MoneyError):
        parse_amount(text)


def test_hidden_a_beta_purchase_is_money_out():
    (book,) = read_beta(["Booking date;Text;Amount", "2025-11-15;Bookshop;(23.90)"], "savings")
    assert book.amount == Money(Decimal("-23.90"))
    assert book.is_expense


# --- Bug 2: no category through the store -----------------------------------------


def test_hidden_no_category_survives_the_store_and_a_later_rule_applies(tmp_path):
    path = tmp_path / "ledger.jsonl"
    store.save(path, [t(-5, text="Bakery"), t(-9, text="Cinema", category="fun")])
    loaded = store.load(path)
    assert [x.category for x in loaded] == [None, "fun"]
    assert [x.category for x in categorize(loaded, [Rule("bakery", "food")])] == ["food", "fun"]


# --- find_transfers ---------------------------------------------------------------


def test_hidden_a_simple_transfer_in_either_order():
    out, inc = t(-500), t(500, account="savings")
    assert find_transfers([out, inc]) == [(out, inc)]
    assert find_transfers([inc, out]) == [(out, inc)]


@pytest.mark.parametrize(("days", "paired"), [(0, True), (3, True), (4, False), (-1, False)])
def test_hidden_the_window_is_zero_to_three_days_after(days, paired):
    out, inc = t(-80), t(80, day=D + timedelta(days=days), account="savings")
    assert find_transfers([out, inc]) == ([(out, inc)] if paired else [])


def test_hidden_what_is_not_a_transfer():
    out = t(-80)
    assert find_transfers([out, t(80)]) == []
    assert find_transfers([out, t("80.01", account="savings")]) == []
    assert find_transfers([out, t(80, account="savings", currency="USD")]) == []
    assert find_transfers([t(80), t(80, account="savings")]) == []
    assert find_transfers([t(-80), t(-80, account="savings")]) == []


def test_hidden_amounts_compare_by_value():
    out, inc = t("-80.00"), t("80", account="savings")
    assert find_transfers([out, inc]) == [(out, inc)]


def test_hidden_one_incoming_is_taken_by_the_earliest_outgoing():
    early = t(-100, day=D, account="checking")
    late = t(-100, day=D + timedelta(days=1), account="cash")
    inc = t(100, day=D + timedelta(days=2), account="savings")
    assert find_transfers([late, inc, early]) == [(early, inc)]


def test_hidden_an_outgoing_takes_the_earliest_incoming():
    out = t(-100)
    later = t(100, day=D + timedelta(days=2), account="savings")
    sooner = t(100, day=D + timedelta(days=1), account="brokerage")
    assert find_transfers([out, later, sooner]) == [(out, sooner)]


def test_hidden_matching_order_and_windows():
    # The first outgoing takes the earliest incoming in its window; one
    # 4 days after it is out of its window but inside the second's.
    first = t(-50, day=D)
    second = t(-50, day=D + timedelta(days=3))
    inc_a = t(50, day=D + timedelta(days=3), account="savings")
    inc_b = t(50, day=D + timedelta(days=4), account="savings")
    assert find_transfers([inc_b, second, inc_a, first]) == [(first, inc_a), (second, inc_b)]
    assert find_transfers([first, second, inc_b]) == [(second, inc_b)]


def test_hidden_ties_keep_the_given_order():
    a = t(-30, text="a")
    b = t(-30, text="b")
    inc1 = t(30, account="savings", text="1")
    inc2 = t(30, account="savings", text="2")
    assert find_transfers([inc1, b, inc2, a]) == [(b, inc1), (a, inc2)]


# --- monthly_totals --------------------------------------------------------------


def test_hidden_both_sides_left_out_across_months():
    out = t(-500, day=date(2025, 11, 30), category="moves")
    inc = t(500, day=date(2025, 12, 2), account="savings", category="moves")
    rent = t(-700, day=date(2025, 12, 1), category="rent")
    assert monthly_totals([out, inc, rent]) == {(2025, 12): {"rent": Money(Decimal("-700"))}}


def test_hidden_an_equal_purchase_next_to_a_transfer_still_counts():
    out = t(-500, category="x")
    twin = t(-500, category="x")
    inc = t(500, account="savings", category="x")
    assert monthly_totals([out, twin, inc]) == {(2025, 11): {"x": Money(Decimal("-500"))}}


def test_hidden_the_report_is_unchanged_without_transfers():
    rows = [t(-10, category="food"), t(-5), t(2000, day=date(2025, 12, 1), category="pay")]
    assert monthly_totals(rows) == {
        (2025, 11): {"food": Money(Decimal("-10")), "uncategorized": Money(Decimal("-5"))},
        (2025, 12): {"pay": Money(Decimal("2000"))},
    }
