# Temperature converter

A small Python module, `convert.py`, with pytest tests in `tests/`.
Standard library only, plus pytest for the tests.

## Milestone 1: Celsius and Fahrenheit
Add `c_to_f(c)` and `f_to_c(f)` to `convert.py`, each returning a float,
with tests.
```acceptance
[{"kind": "file_contains", "path": "convert.py", "contains": "def c_to_f"}]
```

## Milestone 2: Kelvin
Add `c_to_k(c)` and `k_to_c(k)`. A temperature below absolute zero
(below 0 K) raises `ValueError`. With tests.
```acceptance
[{"kind": "file_contains", "path": "convert.py", "contains": "def k_to_c"}, {"kind": "file_exists", "path": "CHANGELOG.md"}]
```
