"""The spreadsheet engine, milestones 1 to 4: every rule the task states.
Test names start with their milestone (m1_ to m4_)."""

import pytest
from sheet import Sheet


def sheet_with(**cells):
    sheet = Sheet()
    for name, text in cells.items():
        sheet.set(name, text)
    return sheet


def value(text, **cells):
    sheet = sheet_with(**cells)
    sheet.set("Z999", text)
    return sheet.get("Z999")


# --- milestone 1: numbers, text and arithmetic ---------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [("42", 42), ("-3.5", -3.5), ("+7", 7), (".25", 0.25), ("  12  ", 12), ("4.0", 4)],
)
def test_m1_numbers(text, expected):
    result = value(text)
    assert result == expected
    assert type(result) is type(expected)


@pytest.mark.parametrize("text", ["1e5", "1,000", "inf", "hello", "12abc", " =1+2", "-"])
def test_m1_text_is_kept_exactly(text):
    assert value(text) == text


def test_m1_an_empty_cell_is_none_and_has_no_text():
    sheet = Sheet()
    assert sheet.get("A1") is None
    assert sheet.text("A1") == ""


def test_m1_setting_empty_text_empties_the_cell():
    sheet = sheet_with(A1="5")
    sheet.set("A1", "")
    assert sheet.get("A1") is None
    assert sheet.text("A1") == ""


def test_m1_text_returns_what_was_put_in():
    sheet = sheet_with(A1="=1 + 2", B1="  7 ")
    assert sheet.text("A1") == "=1 + 2"
    assert sheet.text("B1") == "  7 "


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("=1+2*3", 7),
        ("=(1+2)*3", 9),
        ("=8/2/2", 2),
        ("=10-4-3", 3),
        ("=-2*3", -6),
        ("=--4", 4),
        ("=+5", 5),
        ("= 1 + 2", 3),
        ("=2*(3+(4-1))", 12),
        ("=1.5*2", 3),
    ],
)
def test_m1_arithmetic(formula, expected):
    assert value(formula) == expected


def test_m1_whole_results_are_ints_and_others_floats():
    assert value("=6/2") == 3 and type(value("=6/2")) is int
    assert value("=7/2") == 3.5 and type(value("=7/2")) is float
    assert type(value("=0.5+0.5")) is int


@pytest.mark.parametrize("name", ["b2", "z999", "A1"])
def test_m1_cell_names_in_any_case(name):
    sheet = Sheet()
    sheet.set(name, "3")
    assert sheet.get(name.upper()) == 3
    assert sheet.get(name.lower()) == 3


@pytest.mark.parametrize("name", ["A0", "AA1", "A1000", "1A", "A", "", "A-1"])
def test_m1_a_bad_cell_name_raises_value_error(name):
    sheet = Sheet()
    with pytest.raises(ValueError):
        sheet.set(name, "1")
    with pytest.raises(ValueError):
        sheet.get(name)
    with pytest.raises(ValueError):
        sheet.text(name)


# --- milestone 2: references ----------------------------------------------


def test_m2_a_reference():
    assert value("=A1+B2*2", A1="1", B2="3") == 7


def test_m2_formulas_follow_changes_through_other_cells():
    sheet = sheet_with(A1="1", B1="=A1*10", C1="=B1+1")
    assert sheet.get("C1") == 11
    sheet.set("A1", "2")
    assert sheet.get("C1") == 21
    sheet.set("B1", "=A1*100")
    assert sheet.get("C1") == 201


def test_m2_an_empty_cell_counts_as_zero():
    assert value("=A1+5") == 5


def test_m2_a_lone_reference_takes_the_cells_value():
    assert value("=A1", A1="hello") == "hello"
    assert value("=A1", A1="2.5") == 2.5
    assert value("=A1") == 0


def test_m2_references_in_lower_case():
    assert value("=a1+b1", A1="2", B1="3") == 5


def test_m2_a_long_chain():
    sheet = Sheet()
    sheet.set("A1", "1")
    for row in range(2, 201):
        sheet.set(f"A{row}", f"=A{row - 1}+1")
    assert sheet.get("A200") == 200


# --- milestone 3: ranges and functions -------------------------------------


def numbers_sheet():
    return sheet_with(A1="1", A2="2", A3="3", B1="10", B2="hello", B3="")


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("=SUM(A1:A3)", 6),
        ("=SUM(A1:B3)", 16),
        ("=SUM(B3:A1)", 16),
        ("=AVERAGE(A1:A3)", 2),
        ("=MIN(A1:B3)", 1),
        ("=MAX(A1:B3)", 10),
        ("=COUNT(A1:B3)", 4),
        ("=sum(A1:A3)", 6),
        ("=Max(A1:A3)", 3),
        ("=SUM(A1:A3, 10, B1*2)", 36),
        ("=MAX(A1:A3) - MIN(A1:A3)", 2),
        ("=SUM(A1, MAX(B1:B3))", 11),
        ("=SUM(A1:A1)", 1),
        ("=AVERAGE(A1:A2)", 1.5),
    ],
)
def test_m3_functions(formula, expected):
    sheet = numbers_sheet()
    sheet.set("D1", formula)
    assert sheet.get("D1") == expected


def test_m3_ranges_leave_out_text_and_empty_cells():
    sheet = sheet_with(A1="hello", A2="", A3="4")
    sheet.set("D1", "=COUNT(A1:A5)")
    sheet.set("D2", "=AVERAGE(A1:A5)")
    assert sheet.get("D1") == 1
    assert sheet.get("D2") == 4


def test_m3_a_formula_whose_value_is_a_number_counts_in_a_range():
    sheet = sheet_with(A1="=2*3", A2="4")
    sheet.set("D1", "=SUM(A1:A2)")
    assert sheet.get("D1") == 10


def test_m3_an_empty_cell_given_alone_counts_as_zero():
    sheet = sheet_with(A2="4")
    sheet.set("D1", "=COUNT(A1, A2)")
    sheet.set("D2", "=AVERAGE(A1, A2)")
    assert sheet.get("D1") == 2
    assert sheet.get("D2") == 2


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("=SUM(C1:C9)", 0),
        ("=MIN(C1:C9)", 0),
        ("=MAX(C1:C9)", 0),
        ("=COUNT(C1:C9)", 0),
        ("=AVERAGE(C1:C9)", "#DIV/0!"),
    ],
)
def test_m3_no_numbers_at_all(formula, expected):
    sheet = sheet_with(C1="text")
    sheet.set("D1", formula)
    assert sheet.get("D1") == expected


@pytest.mark.parametrize("formula", ["=A1:A3", "=A1:A3+1", "=SUM(A1:A3+1)"])
def test_m3_a_range_outside_a_function_argument_is_value_error(formula):
    sheet = numbers_sheet()
    sheet.set("D1", formula)
    assert sheet.get("D1") == "#VALUE!"


def test_m3_functions_follow_changes():
    sheet = numbers_sheet()
    sheet.set("D1", "=SUM(A1:A3)")
    sheet.set("A2", "20")
    assert sheet.get("D1") == 24


# --- milestone 4: errors ---------------------------------------------------


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("=1/0", "#DIV/0!"),
        ("=5/(2-2)", "#DIV/0!"),
        ("=A0", "#REF!"),
        ("=AA1+1", "#REF!"),
        ("=B1000", "#REF!"),
        ("=SUM(A0:A3)", "#REF!"),
        ("=FOO(1)", "#NAME?"),
        ("=TOTAL", "#NAME?"),
        ("=1+", "#ERROR!"),
        ("=(1", "#ERROR!"),
        ("=2 3", "#ERROR!"),
        ("=", "#ERROR!"),
        ("=SUM(1,)", "#ERROR!"),
        ("=1+*2", "#ERROR!"),
        ("=A0+", "#ERROR!"),
        ("=1/0+A0", "#DIV/0!"),
        ("=A0+1/0", "#REF!"),
        ("=FOO(1)+A0", "#NAME?"),
    ],
)
def test_m4_errors(formula, expected):
    assert value(formula) == expected


def test_m4_text_in_arithmetic_is_value_error():
    assert value("=A1+1", A1="hello") == "#VALUE!"
    assert value("=-A1", A1="hello") == "#VALUE!"
    assert value("=SUM(A1, 1)", A1="hello") == "#VALUE!"


def test_m4_errors_spread_through_cells_and_ranges():
    sheet = sheet_with(A1="=1/0", A2="=A1+1", A3="5")
    sheet.set("B1", "=SUM(A1:A3)")
    sheet.set("B2", "=A2*2")
    sheet.set("B3", "=MAX(A3, A2)")
    assert sheet.get("A2") == "#DIV/0!"
    assert sheet.get("B1") == "#DIV/0!"
    assert sheet.get("B2") == "#DIV/0!"
    assert sheet.get("B3") == "#DIV/0!"


def test_m4_a_lone_reference_to_an_error_is_that_error():
    assert value("=A1", A1="=FOO(2)") == "#NAME?"


def test_m4_text_that_looks_like_an_error_is_text():
    sheet = sheet_with(A1="#DIV/0!", A2="3")
    sheet.set("B1", "=SUM(A1:A2)")
    sheet.set("B2", "=A1+1")
    assert sheet.get("A1") == "#DIV/0!"
    assert sheet.get("B1") == 3
    assert sheet.get("B2") == "#VALUE!"


def test_m4_a_cell_that_depends_on_itself():
    assert value("=Z999+1") == "#CYCLE!"


def test_m4_every_cell_of_a_cycle():
    sheet = sheet_with(A1="=B1", B1="=C1+1", C1="=A1*2")
    assert [sheet.get(c) for c in ("A1", "B1", "C1")] == ["#CYCLE!"] * 3


def test_m4_a_range_can_make_a_cycle():
    sheet = sheet_with(A2="1", A3="2", A1="=SUM(A1:A3)")
    assert sheet.get("A1") == "#CYCLE!"


def test_m4_a_cell_in_a_cycle_is_cycle_whatever_else_its_formula_holds():
    sheet = sheet_with(A1="=1/0+B1", B1="=A1")
    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.get("B1") == "#CYCLE!"


def test_m4_a_cell_that_uses_a_cycle_gets_the_error():
    sheet = sheet_with(A1="=B1", B1="=A1", C1="=A1+1", D1="=1/0+A1")
    assert sheet.get("C1") == "#CYCLE!"
    assert sheet.get("D1") == "#DIV/0!"


def test_m4_breaking_the_cycle_brings_values_back():
    sheet = sheet_with(A1="=B1+1", B1="=A1")
    assert sheet.get("A1") == "#CYCLE!"
    sheet.set("B1", "5")
    assert sheet.get("A1") == 6
    assert sheet.get("B1") == 5


def test_m4_fixing_a_cell_clears_the_error_downstream():
    sheet = sheet_with(A1="=1/0", B1="=A1+1")
    assert sheet.get("B1") == "#DIV/0!"
    sheet.set("A1", "2")
    assert sheet.get("B1") == 3
