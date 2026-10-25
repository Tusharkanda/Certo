# Certo v0.1.25

Not released yet.

## New: independent tests can change the verdict

`--independent-tests-strict` (or `CERTO_INDEPENDENT_TESTS_STRICT=yes`)
turns [independent tests](../guides/independent-tests.md) on and lets
them decide: when the project's checks pass but most sets of independent
tests fail, the verdict is `independent_failed` instead of `verified`,
and Certo exits with 1.

```text
Verification: independent_failed
Independent tests: failed, 2 of 3 sets failed (written from the task by m).
```

Only a `failed` result changes the verdict; `split`, `none` and
`couldn't run` leave `verified` as it is, and other verdicts stay as
they are. `--independent-tests` alone is still report only. The choice
comes from the 0.1.24 measurements: the tests caught 7 of 8 runs that
had fooled Certo on saved projects, and failed 1 of 38 right runs in
live ones, with a wrong test. So strict is for scripts and pipelines
where a false `verified` costs more than a second look. See
[Make them change the verdict](../guides/independent-tests.md#make-them-change-the-verdict)
and [`independent_failed`](../guides/after-the-verdict.md#independent_failed).
