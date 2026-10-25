# Check files changed by benchmark runs (Certo 0.1.24)

Since 0.1.24, a `verified` run lists the test files and check settings
the agent changed or deleted (see
[Changed check files](../reference/verdicts.md#changed-check-files)).
Does weakening a test explain any of the runs that fooled Certo? To find
out without running anything again, the projects saved by earlier
`certo bench` runs were compared with their task's starter files.

## The setup

- **Certo:** 0.1.24 (not released yet), from a source checkout.
  **Run:** 2026-10-25, with `scripts/count_check_file_changes.py`. No
  model was called.
- **Projects:** 379 projects saved by earlier benchmark runs (Certo 0.1.13
  to 0.1.23, local and cloud models), kept only when the run started after
  the task's starter last changed. Certo had said `verified` on 300; on
  8 of those the hidden tests failed, so Certo was fooled.
- **Check files:** each starter's test files and check settings, as
  Certo counts them. Five of the 13 starters have none (their projects
  start with no tests); `ledger-transfers` has 9; the others 1.

## Results

| Runs | A check file changed | Test lines removed, or a test deleted |
|---|---|---|
| All | 35 of 379 | 0 of 379 |
| `verified`, hidden tests passed | 33 of 292 | 0 of 292 |
| `verified`, hidden tests failed (fooled) | 0 of 8 | 0 of 8 |
| Not `verified` | 2 of 79 | 0 of 79 |

- **No run weakened a test.** Every change added tests, or rewrote a
  line in place: 31 of the 35 are `inventory-fix`, whose task asks for
  new tests in the starter's test file; those runs extended its import
  line and added tests below.
- **The runs that fooled Certo didn't touch a check file.** They passed
  the project's own tests honestly; the tests just didn't cover what the
  hidden tests check. That is what
  [independent tests](independent-tests-replay-0.1.24.md) are for.
- **The first count was misleading.** Counting a rewritten line as one
  removed and one added made 30 of the 31 `inventory-fix` runs look like
  they removed a test line. Certo now counts it as one line changed.

So the list stays a report: on this data, a rule that turned removed
test lines into a failure would never have fired.

## Limits

- **Few starters have tests.** Five tasks start with no check files at
  all, so there was nothing to weaken there. A task whose starter has a
  test in the way of the easy solution would test this better.
- **Benchmark tasks never ask for a test to be weakened,** and no model
  was pushed to. Real projects, with long-failing or flaky tests, may
  differ.

## Reproduce it

With `certo bench` results in `bench-results/`:

```bash
uv run python scripts/count_check_file_changes.py --results bench-results \
    --out bench-results/check-file-changes.md
```

## Related

- [Changed check files](../reference/verdicts.md#changed-check-files)
- [Independent tests on saved projects](independent-tests-replay-0.1.24.md)
