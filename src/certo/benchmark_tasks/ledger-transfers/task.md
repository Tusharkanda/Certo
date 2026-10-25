# Fix two ledger bugs and leave transfers out of the report

This folder is `ledger`, a small Python package that imports bank CSV
statements, categorizes transactions and reports totals by month (see
`README.md`). Fix the two bugs below and add the feature. Use only the
standard library, and keep the existing tests passing.

## Bug 1: Beta Bank purchases show up as income

Beta Bank writes money out in parentheses, as `(23.90)`, but after an
import those purchases have a positive amount, so the monthly report
counts them as money in. An amount in parentheses must be negative:
`(23.90)` is -23.90 and `(1,234.50)` is -1234.50. An amount with only
one parenthesis, empty parentheses, or a sign inside them (`(-5)`) is
not an amount: it raises `MoneyError`, as other unreadable amounts do.

## Bug 2: uncategorized transactions never get a category

A transaction imported before there was a rule for it is stored without
a category. After the store is loaded again, it has the category
`"None"` (a string), so adding a rule later never categorizes it. A
transaction without a category must stay without one (`None`) through
`store.save` and `store.load`.

## Feature: transfers between your own accounts

Moving money from checking to savings is neither spending nor income,
but today it shows up as both. Add `ledger/transfers.py` with:

```python
def find_transfers(transactions) -> list[tuple[Transaction, Transaction]]:
```

It returns the transfers among `transactions` as `(outgoing, incoming)`
pairs. Only the sign of the amount says which side a transaction is on:
a negative amount is outgoing, a positive one is incoming. The account
and the description never decide it. An outgoing and an incoming
transaction are a transfer when all of these hold:

- they are in different accounts;
- they are the same amount apart from the sign, in the same currency;
- the incoming one is dated 0 to 3 days after the outgoing one
  (3 days included), never before it.

Each transaction is part of at most one transfer. Outgoing transactions
are matched one at a time, earliest date first (on the same date, in the
order given); each takes the earliest incoming match not already taken
(on the same date, the first in the order given). The returned list is
in that matching order. The descriptions don't matter.

Then `reports.monthly_totals` must leave out every transaction that is
part of a transfer, so neither side counts in any month, even when the
two sides fall in different months. Nothing else in the report changes.

Add tests for both fixes and for `find_transfers` to `tests/`.
