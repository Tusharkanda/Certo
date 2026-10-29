# Spreadsheet engine

Build a small spreadsheet engine in Python, in one file, `sheet.py`,
using only the standard library. Write pytest tests for it in `tests/`.

The engine is a class, `Sheet`:

- `Sheet()` makes an empty sheet.
- `sheet.set(cell, text)` puts `text` (a string) in a cell. `sheet.set(cell, "")`
  empties it.
- `sheet.get(cell)` returns the cell's value, always up to date with
  every cell it depends on.
- `sheet.text(cell)` returns the text that was put in the cell, or `""`.

A cell name is one letter `A` to `Z` and a row number `1` to `999`, such
as `A1`, `C12` or `Z999`, in any case: `b2` is `B2`. Any other name
given to `set`, `get` or `text` raises `ValueError`.

## Milestone 1: numbers, text and arithmetic

- Text that is a number, after taking away spaces at both ends, holds
  that number: an optional `+` or `-`, digits, and an optional decimal
  part, such as `42`, `-3.5`, `+7` or `.25`. Nothing else is a number:
  `1e5`, `1,000` and `inf` are text.
- Text that starts with `=` is a formula. Any other text is text: its
  value is the text exactly as it was put in.
- The value of an empty cell is `None`.
- A number's value is a Python `int` when it is whole and a `float`
  otherwise: `get` of `"4"` and of `"4.0"` is `4`, of `"2.5"` is `2.5`.
  The same goes for a formula's result: `=7/2` is `3.5`, `=6/2` is `3`.
- A formula may use numbers (digits with an optional decimal part),
  `+`, `-`, `*`, `/`, parentheses, and a unary `-` or `+`, with the
  usual order: `*` and `/` before `+` and `-`, left to right, so
  `=1+2*3` is `7`, `=(1+2)*3` is `9`, `=8/2/2` is `2`, `=-2*3` is `-6`.
  Spaces are allowed between the parts: `= 1 + 2` is `3`.
```acceptance
[{"kind": "file_exists", "path": "sheet.py"}]
```

## Milestone 2: references

- A formula may name another cell, such as `=A1+B2*2`. Its value is that
  cell's value now: change `A1`, and every formula that depends on it,
  directly or through other cells, gives the new result.
- In arithmetic, an empty cell counts as `0`.
- A formula that is only a reference to one cell, such as `=A1`, has
  that cell's value, whatever it is: a number, a text, or an error (see
  milestone 4). An empty cell gives `0`.

## Milestone 3: ranges and functions

- A range is two cell names with `:` between them, such as `A1:B3`: every
  cell of the rectangle between them, both included. `B3:A1` is the same
  range.
- A formula may call `SUM`, `AVERAGE`, `MIN`, `MAX` and `COUNT`, in any
  case (`sum` is `SUM`). Their arguments are separated by commas, and
  each one is a range or any expression: `=SUM(A1:A3, 10, B1*2)`.
  Functions can be used inside expressions and inside each other:
  `=MAX(A1:A3) - MIN(A1:A3)`, `=SUM(A1, MAX(B1:B3))`.
- From a range, the functions use only the cells that hold numbers:
  text cells and empty cells are left out. An argument that is not a
  range is used even when it comes from an empty cell, as `0`.
- `SUM` adds the numbers, `AVERAGE` gives their mean, `MIN` and `MAX` the
  smallest and largest, `COUNT` how many there are. With no numbers at
  all, `SUM`, `MIN`, `MAX` and `COUNT` give `0`, and `AVERAGE` gives the
  error `#DIV/0!`.
- A range anywhere other than as a function's argument, such as `=A1:A3`
  or `=A1:A3+1`, is the error `#VALUE!`.

## Milestone 4: errors

An error is a value too: `get` returns it as a string.

- `#DIV/0!`: a division by zero.
- `#VALUE!`: text used in arithmetic or in a function argument that is
  not a range (`=A1+1` when `A1` holds `hello`), or a range used outside
  a function.
- `#REF!`: a reference that is not a cell name, such as `A0`, `AA1` or
  `B1000`: letters followed by digits that aren't a valid cell name.
- `#NAME?`: a call to a function that doesn't exist, such as `=FOO(1)`,
  or a word that is neither a cell name nor a function call, such as
  `=TOTAL`.
- `#ERROR!`: a formula that can't be read, such as `=1+`, `=(1`, `=2 3`,
  `=` or `=SUM(1,)`. This is checked before anything else in the
  formula: `=A0+` is `#ERROR!`.
- `#CYCLE!`: a formula that depends on itself, directly (`A1` is `=A1`)
  or through other cells (`A1` is `=B1`, `B1` is `=A1`). A range counts:
  `A1` holding `=SUM(A1:A3)` depends on itself. Every cell of the cycle
  is `#CYCLE!`, whatever else its formula holds. Once the cycle is
  broken, the cells give their values again.

An error spreads: a formula that uses a cell or a value that is an error
has that error as its value, also through a range in a function. When
there are several, the first one met reading the formula from left to
right wins: `=1/0+A0` is `#DIV/0!`, `=A0+1/0` is `#REF!`. A text cell
that happens to look like an error, such as one holding `#DIV/0!`, is
only text.
```acceptance
[{"kind": "file_contains", "path": "sheet.py", "contains": "#CYCLE!"}]
```

## Milestone 5: files and the command line

- `sheet.save(path)` writes the sheet to a CSV file, with Python's `csv`
  module and its default format: one row per sheet row from row 1 to
  the last row that has a cell, and one column per letter from `A` to
  the last column that has a cell. Each field holds the cell's text, not
  its value (`=1+2`, not `3`); an empty cell is an empty field.
- `Sheet.load(path)` is a class method that reads such a file back into
  a new sheet: the field in row `r`, column `c` is the text of that cell,
  and empty fields leave cells empty.
- `python sheet.py [FILE]` runs the sheet from the command line. With a
  `FILE` that exists, it starts from that file. Then it reads commands
  from standard input, one per line:
  - `set CELL TEXT`: puts `TEXT` in the cell. `TEXT` is the rest of the
    line after one space and may hold spaces; with nothing after the
    cell name, the cell is emptied. Prints nothing.
  - `get CELL`: prints the cell's value on one line: a number with
    Python's `format(value, ".10g")` (so `3.5`, `7`, `0.3333333333`), a
    text or an error as it is, and an empty line for an empty cell.
  - `save`: writes the sheet to `FILE`. Without a `FILE`, it is an error.
  - An empty line is ignored. Anything else, including a wrong cell name
    and `save` without a `FILE`, prints a line starting with `Error:` to
    standard error, and the program goes on with the next line.

  When standard input ends, the program exits with code 0.
```acceptance
[{"kind": "file_contains", "path": "sheet.py", "contains": "__main__"}]
```
