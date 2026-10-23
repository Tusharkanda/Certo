from datetime import date
from decimal import Decimal

from ledger.money import Money
from ledger.reports import balances, format_report, monthly_totals
from tests.helpers import tx


def test_monthly_totals_per_category():
    totals = monthly_totals(
        [
            tx("Shop", -10, category="groceries", day=date(2025, 11, 1)),
            tx("Shop", "-5.50", category="groceries", day=date(2025, 11, 20)),
            tx("Salary", 2000, category="income", day=date(2025, 11, 3)),
            tx("Mystery", -1, day=date(2025, 12, 1)),
        ]
    )
    assert list(totals) == [(2025, 11), (2025, 12)]
    assert totals[(2025, 11)]["groceries"] == Money(Decimal("-15.50"))
    assert totals[(2025, 11)]["income"] == Money(Decimal("2000"))
    assert totals[(2025, 12)] == {"uncategorized": Money(Decimal("-1"))}


def test_balances_per_account_and_currency():
    result = balances(
        [tx("a", 10), tx("b", -3), tx("c", 7, account="savings"), tx("d", 1, currency="USD")]
    )
    assert result == {
        ("checking", "EUR"): Money(Decimal("7")),
        ("checking", "USD"): Money(Decimal("1"), "USD"),
        ("savings", "EUR"): Money(Decimal("7")),
    }


def test_format_report():
    text = format_report([tx("Shop", "-10.5", category="groceries")])
    assert text.splitlines()[0] == "2025-11"
    assert "groceries" in text and "-10.50 EUR" in text
    assert format_report([], (2025, 1)) == "No transactions."
