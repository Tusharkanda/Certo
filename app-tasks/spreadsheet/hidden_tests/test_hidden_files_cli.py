"""The spreadsheet engine, milestone 5: CSV files and the command line,
run as people run it. Test names start with m5_."""

import csv
import subprocess
import sys
from pathlib import Path

from sheet import Sheet

PROGRAM = Path.cwd() / "sheet.py"


def run(*args, lines=(), timeout=20):
    text = "".join(f"{line}\n" for line in lines)
    return subprocess.run(
        [sys.executable, str(PROGRAM), *map(str, args)],
        input=text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


# --- save and load ----------------------------------------------------------


def test_m5_save_writes_the_texts_in_a_grid(tmp_path):
    sheet = Sheet()
    sheet.set("A1", "1")
    sheet.set("C1", "=A1+1")
    sheet.set("B3", "hello, world")
    path = tmp_path / "s.csv"
    sheet.save(str(path))
    assert rows(path) == [["1", "", "=A1+1"], ["", "", ""], ["", "hello, world", ""]]


def test_m5_save_of_an_empty_sheet_has_no_rows(tmp_path):
    path = tmp_path / "s.csv"
    Sheet().save(str(path))
    assert rows(path) == []


def test_m5_load_reads_a_saved_sheet_back(tmp_path):
    sheet = Sheet()
    sheet.set("A1", "2")
    sheet.set("A2", "=A1*3")
    sheet.set("B1", 'say "hi"')
    path = tmp_path / "s.csv"
    sheet.save(str(path))
    loaded = Sheet.load(str(path))
    assert isinstance(loaded, Sheet)
    assert loaded.get("A2") == 6
    assert loaded.text("A2") == "=A1*3"
    assert loaded.get("B1") == 'say "hi"'
    assert loaded.get("B2") is None


def test_m5_load_reads_a_csv_written_by_hand(tmp_path):
    path = tmp_path / "s.csv"
    path.write_text("1,2,=SUM(A1:B1)\n,,\n", encoding="utf-8")
    loaded = Sheet.load(str(path))
    assert loaded.get("C1") == 3
    assert loaded.text("A2") == ""


# --- the command line -------------------------------------------------------


def test_m5_set_and_get(tmp_path):
    result = run(lines=["set A1 3.5", "set A2 =A1*2", "get A1", "get A2", "get A3"])
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["3.5", "7", ""]


def test_m5_numbers_are_printed_with_ten_significant_digits():
    result = run(lines=["set A1 =1/3", "set A2 =2/3*3000000", "get A1", "get A2"])
    assert result.stdout.splitlines() == ["0.3333333333", "2000000"]


def test_m5_text_and_errors_are_printed_as_they_are():
    result = run(lines=["set A1 hello there", "set A2 =1/0", "get A1", "get A2"])
    assert result.stdout.splitlines() == ["hello there", "#DIV/0!"]


def test_m5_set_with_nothing_after_the_cell_empties_it():
    result = run(lines=["set A1 5", "set A1", "get A1"])
    assert result.stdout.splitlines() == [""]


def test_m5_errors_go_to_standard_error_and_the_program_goes_on():
    result = run(lines=["fly", "set A0 1", "get AA1", "save", "set A1 2", "get A1"])
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["2"]
    errors = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(errors) == 4
    assert all(line.startswith("Error:") for line in errors)


def test_m5_empty_lines_are_ignored():
    result = run(lines=["", "set A1 1", "", "get A1"])
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["1"]
    assert result.stderr.strip() == ""


def test_m5_save_writes_the_file_and_a_new_run_starts_from_it(tmp_path):
    path = tmp_path / "budget.csv"
    first = run(path, lines=["set A1 100", "set A2 =A1*2", "save"])
    assert first.returncode == 0
    assert rows(path) == [["100"], ["=A1*2"]]
    second = run(path, lines=["get A2", "set A1 1", "get A2"])
    assert second.stdout.splitlines() == ["200", "2"]


def test_m5_a_file_that_does_not_exist_yet_starts_empty(tmp_path):
    path = tmp_path / "new.csv"
    result = run(path, lines=["get A1", "set B2 x", "save"])
    assert result.returncode == 0
    assert result.stdout.splitlines() == [""]
    assert rows(path) == [["", ""], ["", "x"]]


def test_m5_the_end_of_input_ends_the_program():
    result = run(lines=[])
    assert result.returncode == 0
