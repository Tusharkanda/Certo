# ledger

Import the CSV statements your banks export, give each transaction a
category, and see what came in and went out each month.

```bash
python -m ledger import samples/alpha.csv --account checking --rules samples/rules.txt
python -m ledger import samples/beta.csv --account savings --rules samples/rules.txt
python -m ledger report --month 2025-11
```

Transactions are kept in `ledger.jsonl` (`--store` to change it).
Importing the same statement twice adds nothing.

## Supported banks

- **Alpha Bank**: `Date,Description,Amount,Currency`, dates as
  `31/12/2025`, signed amounts.
- **Beta Bank**: `Booking date;Text;Amount`, ISO dates, money out in
  parentheses: `(12.50)`. Pass `--currency` if the account isn't in EUR.

## Rules

One rule per line, `pattern => category`. The first rule whose pattern
appears in the description wins (case doesn't matter). A transaction
that already has a category keeps it.

## Development

Standard library only. Run the tests with `python -m pytest`.
