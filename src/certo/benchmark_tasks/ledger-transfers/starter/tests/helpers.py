from datetime import date
from decimal import Decimal

from ledger.models import Transaction
from ledger.money import Money


def tx(
    description, amount, *, day=date(2025, 11, 5), account="checking", category=None, currency="EUR"
):
    return Transaction(
        date=day,
        description=description,
        amount=Money(Decimal(str(amount)), currency),
        account=account,
        category=category,
    )
