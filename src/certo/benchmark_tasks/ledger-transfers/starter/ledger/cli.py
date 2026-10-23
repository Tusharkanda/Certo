"""`ledger import` and `ledger report`."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from . import store
from .categorize import RuleError, categorize, load_rules
from .importers import ImportError_, import_file
from .reports import format_report

DEFAULT_STORE = "ledger.jsonl"


def _month(text: str) -> tuple[int, int]:
    try:
        parsed = datetime.strptime(text, "%Y-%m")
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM, got {text!r}") from None
    return (parsed.year, parsed.month)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledger", description=__doc__)
    parser.add_argument("--store", default=DEFAULT_STORE, help="the JSON Lines store")
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="add a bank statement to the store")
    imp.add_argument("file")
    imp.add_argument("--account", required=True, help="your name for the account")
    imp.add_argument("--currency", default="EUR", help="for Beta Bank files")
    imp.add_argument("--rules", help="a rules file to categorize with")

    rep = sub.add_parser("report", help="totals per month and category")
    rep.add_argument("--month", type=_month, help="only this month, YYYY-MM")
    rep.add_argument("--rules", help="categorize with these rules first")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        transactions = store.load(args.store)
        rules = load_rules(args.rules) if args.rules else []
        if args.command == "import":
            new = import_file(args.file, args.account, args.currency)
            merged = store.merge(transactions, new)
            store.save(args.store, categorize(merged, rules))
            print(f"Imported {len(merged) - len(transactions)} new transaction(s).")
            return 0
        print(format_report(categorize(transactions, rules), args.month))
        return 0
    except (ImportError_, RuleError, store.StoreError, OSError) as exc:
        print(f"ledger: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
