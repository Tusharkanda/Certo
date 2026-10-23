from datetime import date
from decimal import Decimal

from ledger.money import Money
from ledger.reports import monthly_totals
from ledger.transfers import find_transfers
from tests.helpers import tx

OUT = date(2025, 11, 12)


def test_a_transfer_between_two_accounts():
    out = tx("To savings", -500, day=OUT)
    inc = tx("From checking", 500, day=date(2025, 11, 13), account="savings")
    assert find_transfers([inc, out]) == [(out, inc)]


def test_up_to_three_days_later_never_earlier():
    out = tx("To savings", -500, day=OUT)
    three = tx("In", 500, day=date(2025, 11, 15), account="savings")
    four = tx("In", 500, day=date(2025, 11, 16), account="savings")
    before = tx("In", 500, day=date(2025, 11, 11), account="savings")
    assert find_transfers([out, three]) == [(out, three)]
    assert find_transfers([out, four]) == []
    assert find_transfers([out, before]) == []


def test_not_a_transfer():
    out = tx("Out", -500, day=OUT)
    assert find_transfers([out, tx("In", 500, day=OUT)]) == []  # same account
    assert find_transfers([out, tx("In", "499.99", day=OUT, account="savings")]) == []
    assert find_transfers([out, tx("In", 500, day=OUT, account="s", currency="USD")]) == []


def test_each_transaction_in_one_transfer_earliest_first():
    first = tx("Out", -100, day=date(2025, 11, 1))
    second = tx("Out", -100, day=date(2025, 11, 2))
    late = tx("In", 100, day=date(2025, 11, 3), account="savings")
    early = tx("In", 100, day=date(2025, 11, 2), account="savings")
    assert find_transfers([second, late, first, early]) == [(first, early), (second, late)]


def test_transfers_are_left_out_of_the_monthly_totals_even_across_months():
    out = tx("To savings", -500, day=date(2025, 11, 30), category="savings")
    inc = tx("From checking", 500, day=date(2025, 12, 1), account="savings", category="savings")
    shop = tx("Shop", -20, day=date(2025, 11, 30), category="groceries")
    assert monthly_totals([out, inc, shop]) == {(2025, 11): {"groceries": Money(Decimal("-20"))}}


def test_an_equal_transaction_outside_the_transfer_still_counts():
    out = tx("Out", -500, day=OUT, category="x")
    twin = tx("Out", -500, day=OUT, category="x")
    inc = tx("In", 500, day=OUT, account="savings", category="x")
    assert monthly_totals([out, twin, inc]) == {(2025, 11): {"x": Money(Decimal("-500"))}}
