from decimal import Decimal

import pytest

from ledger.money import Money, MoneyError, parse_amount, total


def test_parse_plain_and_signed_amounts():
    assert parse_amount("12.50") == Decimal("12.50")
    assert parse_amount("-12.50") == Decimal("-12.50")
    assert parse_amount("+3") == Decimal("3")
    assert parse_amount(" 7.25 ") == Decimal("7.25")


def test_parse_drops_thousands_separators():
    assert parse_amount("1,234.56") == Decimal("1234.56")
    assert parse_amount("-12,000") == Decimal("-12000")


@pytest.mark.parametrize("text", ["", "   ", "abc", "1.2.3", "NaN", "Infinity"])
def test_parse_rejects_what_isnt_an_amount(text):
    with pytest.raises(MoneyError):
        parse_amount(text)


def test_money_needs_a_decimal_and_a_currency_code():
    with pytest.raises(MoneyError):
        Money(12.5, "EUR")
    with pytest.raises(MoneyError):
        Money(Decimal("1"), "euro")


def test_adding_different_currencies_is_an_error():
    with pytest.raises(MoneyError):
        Money(Decimal("1"), "EUR") + Money(Decimal("1"), "USD")


def test_format_rounds_half_away_from_zero():
    assert Money(Decimal("1234.5"), "EUR").format() == "1,234.50 EUR"
    assert Money(Decimal("-0.125"), "EUR").format() == "-0.13 EUR"


def test_total():
    amounts = [Money(Decimal("1.10")), Money(Decimal("-0.10"))]
    assert total(amounts) == Money(Decimal("1.00"))
    assert total([], "USD") == Money.zero("USD")
