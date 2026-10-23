from pathlib import Path

from ledger.cli import main

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_import_twice_adds_nothing_the_second_time(tmp_path, capsys):
    db = str(tmp_path / "ledger.jsonl")
    assert main(["--store", db, "import", str(SAMPLES / "alpha.csv"), "--account", "checking"]) == 0
    assert main(["--store", db, "import", str(SAMPLES / "alpha.csv"), "--account", "checking"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["Imported 5 new transaction(s).", "Imported 0 new transaction(s)."]


def test_report_for_one_month(tmp_path, capsys):
    db = str(tmp_path / "ledger.jsonl")
    rules = str(SAMPLES / "rules.txt")
    main(
        [
            "--store",
            db,
            "import",
            str(SAMPLES / "alpha.csv"),
            "--account",
            "checking",
            "--rules",
            rules,
        ]
    )
    capsys.readouterr()
    assert main(["--store", db, "report", "--month", "2025-11"]) == 0
    report = capsys.readouterr().out
    assert "groceries" in report and "-127.45 EUR" in report


def test_a_bad_file_is_reported_not_raised(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text("when,what\n")
    assert main(["--store", str(tmp_path / "s.jsonl"), "import", str(bad), "--account", "x"]) == 1
    assert "unknown statement format" in capsys.readouterr().err
