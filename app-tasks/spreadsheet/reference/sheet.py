"""A small spreadsheet engine: the reference solution of the task."""

from __future__ import annotations

import csv
import os
import re
import sys

_CELL = re.compile(r"^[A-Za-z][1-9][0-9]{0,2}$")
_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")
_TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d*)?|\.\d+)|([A-Za-z][A-Za-z0-9]*)|(.))")
_REFLIKE = re.compile(r"^[A-Za-z]+[0-9]+$")
_FUNCTIONS = ("SUM", "AVERAGE", "MIN", "MAX", "COUNT")


class Error(str):
    """An error value: a string that isn't a text cell's text."""


DIV0 = Error("#DIV/0!")
VALUE = Error("#VALUE!")
REF = Error("#REF!")
NAME = Error("#NAME?")
SYNTAX = Error("#ERROR!")
CYCLE = Error("#CYCLE!")


class _SyntaxError(Exception):
    pass


def _cell_name(name: str) -> str:
    if not isinstance(name, str) or not _CELL.match(name):
        raise ValueError(f"not a cell name: {name!r}")
    return name.upper()


def _number(value: float):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _tokens(text: str) -> list[tuple[str, str]]:
    tokens = []
    pos = 0
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        match = _TOKEN.match(text, pos)
        number, word, other = match.groups()
        if number is not None:
            tokens.append(("num", number))
        elif word is not None:
            tokens.append(("word", word))
        elif other in "+-*/(),:":
            tokens.append(("op", other))
        else:
            raise _SyntaxError(other)
        pos = match.end()
    return tokens


class _Parser:
    def __init__(self, text: str) -> None:
        self.tokens = _tokens(text)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else (None, None)

    def take(self, kind=None, value=None):
        token = self.peek()
        if token[0] is None or (kind and token[0] != kind) or (value and token[1] != value):
            raise _SyntaxError(token)
        self.pos += 1
        return token

    def parse(self):
        if not self.tokens:
            raise _SyntaxError("empty")
        node = self.expr()
        if self.pos != len(self.tokens):
            raise _SyntaxError(self.peek())
        return node

    def expr(self):
        node = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            node = ("bin", op, node, self.term())
        return node

    def term(self):
        node = self.unary()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            node = ("bin", op, node, self.unary())
        return node

    def unary(self):
        if self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            return ("neg" if op == "-" else "pos", self.unary())
        return self.primary()

    def primary(self):
        kind, value = self.peek()
        if kind == "num":
            self.take()
            return ("num", _number(float(value)))
        if (kind, value) == ("op", "("):
            self.take()
            node = self.expr()
            self.take("op", ")")
            return node
        if kind == "word":
            self.take()
            if self.peek() == ("op", "("):
                self.take()
                args = []
                if self.peek() != ("op", ")"):
                    args.append(self.expr())
                    while self.peek() == ("op", ","):
                        self.take()
                        args.append(self.expr())
                self.take("op", ")")
                return ("call", value.upper(), args)
            if self.peek() == ("op", ":"):
                self.take()
                end = self.take("word")[1]
                if not (_REFLIKE.match(value) and _REFLIKE.match(end)):
                    raise _SyntaxError(":")
                return ("range", value, end)
            if _REFLIKE.match(value):
                return ("ref", value)
            return ("name", value)
        raise _SyntaxError((kind, value))


def _range_cells(start: str, end: str) -> list[str] | None:
    if not (_CELL.match(start) and _CELL.match(end)):
        return None
    a, b = start.upper(), end.upper()
    cols = sorted((a[0], b[0]))
    rows = sorted((int(a[1:]), int(b[1:])))
    return [
        f"{chr(c)}{r}"
        for r in range(rows[0], rows[1] + 1)
        for c in range(ord(cols[0]), ord(cols[1]) + 1)
    ]


def _references(node) -> list[str]:
    kind = node[0]
    if kind == "ref":
        return [node[1].upper()] if _CELL.match(node[1]) else []
    if kind == "range":
        return _range_cells(node[1], node[2]) or []
    if kind == "bin":
        return _references(node[2]) + _references(node[3])
    if kind in ("neg", "pos"):
        return _references(node[1])
    if kind == "call":
        return [cell for arg in node[2] for cell in _references(arg)]
    return []


class Sheet:
    def __init__(self) -> None:
        self._text: dict[str, str] = {}
        self._parsed: dict[str, object] = {}

    def set(self, cell: str, text: str) -> None:
        cell = _cell_name(cell)
        if text == "":
            self._text.pop(cell, None)
            self._parsed.pop(cell, None)
            return
        self._text[cell] = text
        if text.startswith("="):
            try:
                self._parsed[cell] = _Parser(text[1:]).parse()
            except _SyntaxError:
                self._parsed[cell] = SYNTAX
        elif _NUMBER.match(text.strip()):
            self._parsed[cell] = ("value", _number(float(text.strip())))
        else:
            self._parsed[cell] = ("value", text)

    def text(self, cell: str) -> str:
        return self._text.get(_cell_name(cell), "")

    def get(self, cell: str):
        return _Evaluation(self).value(_cell_name(cell))

    def save(self, path: str) -> None:
        cells = list(self._text)
        rows = max((int(c[1:]) for c in cells), default=0)
        cols = max((ord(c[0]) - ord("A") + 1 for c in cells), default=0)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for r in range(1, rows + 1):
                writer.writerow(
                    [self._text.get(f"{chr(ord('A') + c)}{r}", "") for c in range(cols)]
                )

    @classmethod
    def load(cls, path: str) -> Sheet:
        sheet = cls()
        with open(path, newline="", encoding="utf-8") as f:
            for r, row in enumerate(csv.reader(f), 1):
                for c, field in enumerate(row[:26]):
                    if field and r <= 999:
                        sheet.set(f"{chr(ord('A') + c)}{r}", field)
        return sheet


class _Evaluation:
    """One `get`: values and cycle membership worked out once each."""

    def __init__(self, sheet: Sheet) -> None:
        self.sheet = sheet
        self.values: dict[str, object] = {}
        self.cyclic: dict[str, bool] = {}

    def deps(self, cell: str) -> list[str]:
        node = self.sheet._parsed.get(cell)
        if not isinstance(node, tuple) or node[0] == "value":
            return []
        return _references(node)

    def in_cycle(self, cell: str) -> bool:
        if cell not in self.cyclic:
            seen = set()
            stack = list(self.deps(cell))
            found = False
            while stack:
                current = stack.pop()
                if current == cell:
                    found = True
                    break
                if current in seen:
                    continue
                seen.add(current)
                stack.extend(self.deps(current))
            self.cyclic[cell] = found
        return self.cyclic[cell]

    def value(self, cell: str):
        """The cell's value; None for an empty cell."""
        if cell in self.values:
            return self.values[cell]
        node = self.sheet._parsed.get(cell)
        if node is None:
            result = None
        elif isinstance(node, Error):
            result = node
        elif node[0] == "value":
            result = node[1]
        elif self.in_cycle(cell):
            result = CYCLE
        else:
            result = self.eval(node)
            if result is None:
                result = 0
        self.values[cell] = result
        return result

    def number(self, node):
        """A node's value for arithmetic: a number, or an error."""
        value = self.eval(node)
        if isinstance(value, Error):
            return value
        if value is None:
            return 0
        if isinstance(value, str):
            return VALUE
        return value

    def eval(self, node):
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "ref":
            if not _CELL.match(node[1]):
                return REF
            return self.value(node[1].upper())
        if kind == "range":
            return REF if _range_cells(node[1], node[2]) is None else VALUE
        if kind == "name":
            return NAME
        if kind in ("neg", "pos"):
            value = self.number(node[1])
            if isinstance(value, Error):
                return value
            return _number(float(-value if kind == "neg" else value))
        if kind == "bin":
            left = self.number(node[2])
            if isinstance(left, Error):
                return left
            right = self.number(node[3])
            if isinstance(right, Error):
                return right
            op = node[1]
            if op == "+":
                return _number(float(left + right))
            if op == "-":
                return _number(float(left - right))
            if op == "*":
                return _number(float(left * right))
            if right == 0:
                return DIV0
            return _number(left / right)
        if kind == "call":
            return self.call(node[1], node[2])
        raise AssertionError(node)

    def call(self, name: str, args):
        if name not in _FUNCTIONS:
            return NAME
        numbers = []
        for arg in args:
            if arg[0] == "range":
                cells = _range_cells(arg[1], arg[2])
                if cells is None:
                    return REF
                for cell in cells:
                    value = self.value(cell)
                    if isinstance(value, Error):
                        return value
                    if isinstance(value, int | float) and not isinstance(value, bool):
                        numbers.append(value)
            else:
                value = self.number(arg)
                if isinstance(value, Error):
                    return value
                numbers.append(value)
        if name == "SUM":
            return _number(float(sum(numbers)))
        if name == "COUNT":
            return len(numbers)
        if name == "AVERAGE":
            return _number(sum(numbers) / len(numbers)) if numbers else DIV0
        if not numbers:
            return 0
        return min(numbers) if name == "MIN" else max(numbers)


def _show(value) -> str:
    if value is None:
        return ""
    if isinstance(value, int | float) and not isinstance(value, Error):
        return format(value, ".10g")
    return str(value)


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else None
    sheet = Sheet.load(path) if path and os.path.exists(path) else Sheet()
    for raw in sys.stdin:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        try:
            if line.startswith("set "):
                cell, _, text = line[4:].partition(" ")
                sheet.set(cell, text)
            elif line.startswith("get "):
                print(_show(sheet.get(line[4:].strip())), flush=True)
            elif line.strip() == "save":
                if path is None:
                    raise ValueError("no file to save to")
                sheet.save(path)
            else:
                raise ValueError(f"unknown command: {line}")
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
