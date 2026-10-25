# Independent tests in live benchmark runs (Certo 0.1.24)

[Independent tests](../guides/independent-tests.md) were first measured
on projects saved by earlier benchmark runs
([Independent tests on saved projects](independent-tests-replay-0.1.24.md)).
This run turns them on while the agent builds, as `--independent-tests`
does, to see what they cost in time and money, and how often they fail
on work that is right.

## The setup

- **Certo:** 0.1.24 (not released yet), from a source checkout.
  **Run:** 2026-10-25, with `--parallel 3`.
- **Model:** `anthropic/claude-haiku-5-5` builds every task and writes
  the independent tests: three sets per run, before the build, with the
  2-of-3 vote.
- **Tasks:** all 13 tasks of task set version 2, three times each: 39
  runs. The benchmark file:
  [`bench-0.1.24-independent.yaml`](bench-0.1.24-independent.yaml).
- **Cost:** $1.71 for the whole benchmark.

## Results

| | Runs |
|---|---|
| `verified` | 39 of 39 |
| Hidden tests passed | 38 of 39 |
| Fooled Certo (`verified`, hidden tests failed) | 1 |
| Independent tests failed (2 of 3 sets) | 1 of 39 |
| ...on runs whose hidden tests passed | 1 of 38 |
| ...on the run that fooled Certo | 0 of 1 |
| One set of three failed, the vote said passed | 8 of 39 |

- **The one false alarm was a wrong test.** On a `duration-parser` run,
  two sets failed on `"2h 5m 10s"`: one expected 7625 seconds, but the
  answer is 7510 (2 × 3600 + 5 × 60 + 10), which the project and the
  reference solution both give. The writer got the arithmetic wrong.
  Three more runs of that task gave the same kind of failure in 2 of
  3 runs, so it isn't rare: one bad sum in a test can turn up in more
  than one set.
- **The one fooled run wasn't caught, and couldn't be from the task
  text.** On `room-bookings`, `DELETE` answered `204` with no body, as
  the task asks, but with a `Content-Type: application/json` header. The
  hidden tests read any response marked as JSON as JSON, so they failed
  on the empty body. The task doesn't mention that header, so tests
  written from the task had no reason to check it.
- **The vote did its job eight times:** one set failed, the other two
  passed, and the result stayed `passed`.

## Time and cost

- **Writing the tests took 34 seconds per run** (median; at most 2
  minutes 21 seconds), against a median run of 1 minute 25 seconds. For
  small tasks that is a large share; for the larger ones it is small
  next to the build.
- **The benchmark cost about twice as much** as the same model without
  independent tests in the 0.1.23 baseline: $0.57 against $0.26 for one
  pass over the 13 tasks, and 33 minutes against 24 of total run time.
  The 0.1.23 numbers are one run per task, so take the comparison as
  rough. The record doesn't split the writing's cost from the build's.

## What it means

- On a strong model the tests rarely fail right work (1 of 38 here), and
  when they do, the failing test is worth reading: here it was wrong.
- They catch what the task states. A rule the task leaves out, like the
  header above, is beyond them.
- This run has only one fooled run, so it says little about how many
  they catch. That number comes from the saved projects: 7 of 8.

## Reproduce it

```bash
certo bench --config docs/benchmark/bench-0.1.24-independent.yaml --parallel 3
```

Each run's result is in `runs/*.json`, under `independent_tests`, with
each set's failing tests (recorded since this run; the first 39 runs
have only each set's pass or fail).

## Related

- [Independent tests](../guides/independent-tests.md)
- [Independent tests on saved projects](independent-tests-replay-0.1.24.md)
- [Benchmark models and strategies](../guides/benchmark.md)
