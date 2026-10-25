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

## Fixed: the run record holds the final verdict

With `CERTO_ARTIFACTS_DIR` set and one model, a run whose acceptance
checks failed was recorded as `verified` in its `metadata.json`, though
Certo printed `acceptance_failed`: the record was written before the
acceptance checks ran. Now it is written after them (and after
`--independent-tests-strict`).

## Fixed: a model call can't outlast the time budget

0.1.24 stopped a run at `CERTO_MAX_TASK_SECONDS`, but a call to the
model already under way still finished, and could be retried: up to
`CERTO_LLM_TIMEOUT_SECONDS` six times (a benchmark run with a local
model spent about 50 minutes on four calls). Now, on local runs, a call
can't wait longer than the time left, and isn't retried once the budget
is gone, so a task ends within seconds of its budget. The work so far is
still checked once, as before. See
[`budget_exhausted`](../troubleshooting.md#budget_exhausted).
