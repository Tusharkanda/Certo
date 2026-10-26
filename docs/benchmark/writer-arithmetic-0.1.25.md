# Benchmark: the independent test writer's expected values, Certo 0.1.25

A replay on saved benchmark projects, comparing two versions of the
instructions for the model that writes
[independent tests](../guides/independent-tests.md). It answers one
question: does telling the writer to compute expected numbers in the
test, instead of by hand, remove the wrong tests that made false alarms?

In the [0.1.24 live runs](independent-tests-live-0.1.24.md), the one
false alarm was a wrong expected value: a test said `"2h 5m 10s"` is
7625 seconds, but it is 7510 (2 × 3600 + 5 × 60 + 10).

## The setup

- **The change:** one new rule in the writer's instructions: work out
  every expected value from the task's rules, check it against the
  task's own examples, and when a number comes from a calculation, write
  the calculation in the test (the rule's example is `12 * 4 + 3`), not
  a number worked out by hand.
- **Writer:** `anthropic/claude-haiku-5-5`, 5 sets of tests per task, for
  all 13 tasks of task set version 2, with each version of the
  instructions: 65 sets each.
- **Projects:** each set ran on 469 saved projects from earlier
  `certo bench` runs (whose hidden-test result is known), on each task's
  reference solution and on its untouched starter.
- **Run:** 2026-10-26, with `scripts/replay_independent_tests.py`; the
  old instructions from Certo `27bd073`.
- **Cost:** $0.58 of writing with the new instructions, $0.52 with the
  old ones. Running the tests is free.

## Results

A set that fails the reference solution has a wrong test.

| | Old instructions | New instructions |
|---|---|---|
| Sets with a wrong test (fail the reference) | 11 of 65 | 0 of 65 |
| ...on `duration-parser` | 4 of 5 | 0 of 5 |
| Right projects failed (false alarms, all sets) | 393 of 1,930 (20%) | 100 of 1,930 (5%) |
| Wrong projects caught (all sets) | 404 of 415 | 399 of 415 |
| Fooled runs caught, by sets that pass the reference | 37 of 40 | 43 of 50 |

- **The arithmetic slips are gone.** With the old instructions, four of
  five `duration-parser` sets got `"2h 5m 10s"` wrong (7410, 7590, 7310
  and 7530 seconds) and failed almost every right project (40 of 200
  passed). With the new ones, every set writes
  `2 * 3600 + 5 * 60 + 10`, and 197 of 200 right projects pass.
- **No real catch was lost.** The old sets seemed to catch more fooled
  `duration-parser` runs, but only because their wrong tests failed
  every project, the reference included. Counting only sets that pass
  the reference, the new instructions caught 43 of 50 fooled runs, the
  old 37 of 40.
- **The other wrong tests vary from run to run.** Besides the sums, the
  old sets had 7 wrong tests that misread the task (`pedestrian-crossing`,
  `room-bookings`, `temperature-table`, `todo-deps`). The new run had
  none, but a first run of the new rule, whose example happened to be
  `duration-parser`'s own answer (so it isn't counted above), had 7
  wrong sets, none of them on `duration-parser`. So the rule fixes the
  sums; for the other wrong tests, the 0 above is likely luck.
- **Small sample:** 5 sets per task and version; one writer model.

## What this means

The rule stays: it removed the wrong numbers it was aimed at, in both
runs of the new instructions, and cost about 10% more to write. Because
`--independent-tests-strict` turns a failing vote into
`independent_failed`, fewer wrong tests means fewer right runs stopped
for nothing. Tests that misread the task are still possible; the 2-of-3
vote is what keeps one of them from deciding the result.

## Reproduce it

Enable `claude-haiku-5-5` in your `models.yaml` and keep the results
folders of earlier benchmarks in `bench-results/`, then:

```bash
uv run python scripts/replay_independent_tests.py --model claude-haiku-5-5 \
    --writes 5 --out bench-results/writer-arith-new
```

For the old instructions, run the same script from a checkout of Certo
`27bd073`.
