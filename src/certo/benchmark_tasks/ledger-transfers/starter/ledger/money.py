"""Money amounts: a Decimal and a currency code, never a float."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


class MoneyError(ValueError):
    """An amount or a currency that can't be read or combined."""


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise MoneyError(f"amount must be a Decimal, not {type(self.amount).__name__}")
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise MoneyError(f"not a currency code: {self.currency!r}")

    @classmethod
    def zero(cls, currency: str = "EUR") -> Money:
        return cls(Decimal("0"), currency)

    def _same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise MoneyError(f"can't combine {self.currency} and {other.currency}")

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    def rounded(self) -> Money:
        """Rounded to the cent, halves away from zero, as banks do."""
        return Money(self.amount.quantize(CENT, rounding=ROUND_HALF_UP), self.currency)

    def format(self) -> str:
        """`-1,234.50 EUR`."""
        value = self.rounded().amount
        sign = "-" if value < 0 else ""
        return f"{sign}{abs(value):,.2f} {self.currency}"

    def __str__(self) -> str:
        return self.format()


def parse_amount(text: str) -> Decimal:
    """Read an amount as banks write it: `1,234.56`, `-12.50`, `+3`.

    Commas are thousands separators and are dropped; spaces around the
    number are ignored.
    """
    cleaned = text.strip().replace(",", "").replace(" ", "")
    cleaned = cleaned.strip("()")
    if not cleaned:
        raise MoneyError(f"not an amount: {text!r}")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise MoneyError(f"not an amount: {text!r}") from None
    if not value.is_finite():
        raise MoneyError(f"not an amount: {text!r}")
    return value


def total(amounts: list[Money], currency: str = "EUR") -> Money:
    """The sum of `amounts`; zero in `currency` when there are none."""
    result = Money.zero(amounts[0].currency if amounts else currency)
    for amount in amounts:
        result = result + amount
    return result
