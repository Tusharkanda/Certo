from datetime import date
from decimal import Decimal

import pytest

from ledger.importers import ImportError_, detect, import_file, read_alpha, read_beta
from ledger.money import Money


def test_alpha_reads_day_first_dates_and_signed_amounts():
    lines = [
        "Date,Description,Amount,Currency",
        '03/11/2025,SALARY ACME LTD,"2,450.00",eur',
        "05/11/2025,Supermarket Fresh,-82.35,EUR",
    ]
    salary, shop = read_alpha(lines, "checking")
    assert salary.date == date(2025, 11, 3)
    assert salary.amount == Money(Decimal("2450.00"), "EUR")
    assert shop.amount == Money(Decimal("-82.35"), "EUR")
    assert shop.account == "checking" and shop.category is None


def test_alpha_reports_the_bad_line():
    lines = ["Date,Description,Amount,Currency", "31/02/2025,Nope,-1.00,EUR"]
    with pytest.raises(ImportError_, match="line 2"):
        read_alpha(lines, "checking")


def test_beta_reads_iso_dates_in_the_given_currency():
    lines = ["Booking date;Text;Amount", "2025-11-30;Interest;1.12"]
    (interest,) = read_beta(lines, "savings", "CHF")
    assert interest.date == date(2025, 11, 30)
    assert interest.amount == Money(Decimal("1.12"), "CHF")


def test_blank_lines_are_skipped():
    lines = ["Booking date;Text;Amount", "", "2025-11-30;Interest;1.12", ";;"]
    assert len(read_beta(lines, "savings")) == 1


def test_detect():
    assert detect("Date,Description,Amount,Currency") == "alpha"
    assert detect("﻿Booking date;Text;Amount\n") == "beta"
    with pytest.raises(ImportError_):
        detect("when,what,how much")


def test_import_file_reads_the_samples(tmp_path):
    path = tmp_path / "alpha.csv"
    path.write_text("Date,Description,Amount,Currency\n01/12/2025,Coffee,-2.40,EUR\n")
    (coffee,) = import_file(path, "checking")
    assert coffee.description == "Coffee"
