# Benchmark: a 60-minute time budget on a local model, Certo 0.1.25

One `certo bench` run on the four larger tasks of task set version 2,
with `qwen3.8:27b` on Ollama, a 32,768-token context window and
condensing on: the same setup as the
[condensing benchmark](context-0.1.25.md), with one change. Each run
gets 60 minutes (`max_task_seconds: 3600`) instead of the default 30. It
answers two questions: does the time budget still stop runs whose work
was right, and does a run stop on time?

## The setup

- **Certo:** 0.1.25 (unreleased, `aec0407`). **Task set:** version 2
  (`6ed42dae4bca`, bundled), its four larger tasks: `ledger-transfers`
  (Python), `library-loans` (Go), `room-bookings` (Node and React) and
  `todo-deps` (Rust).
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Local model:** `ollama/qwen3.8:27b`, on Ollama 0.40.6 on another
  machine. The arm asks Ollama for a 32,768-token window with every
  request (`context_tokens: 32768`); the server's own default is
  131,072 tokens. While the benchmark ran, Ollama reported the model
  loaded with 32,768.
- **Run:** 2026-10-26, one run at a time, 2 repeats: 8 runs. Repeat 1
  ran from 15:36 UTC. The Ollama machine shut down during repeat 2, so
  its four runs ended with a network error; they were run again from
  18:55 UTC with `--resume`, and only those runs are counted.
- **File:** [bench-0.1.25-budget.yaml](bench-0.1.25-budget.yaml).
  **Results folder:** `bench-results/budget-0.1.25`, on the machine that
  ran it.

## Results

| | 60 minutes (this run) | 30 minutes ([condensing benchmark](context-0.1.25.md)) |
|---|---|---|
| Hidden tests passed | 2/8 | 3/8 |
| Verified | 2/8 | 3/8 |
| Fooled | 1 | 1 |
| Ended `budget_exhausted` | 2 | 5 |
| Ended in minutes, tool call written as text | 4 | 1 |

| Task | Repeat | Verdict | Hidden tests | Time | Tests in the project |
|---|---|---|---|---|---|
| ledger-transfers | 1 | `verified` | failed (fooled) | 33m 10s | yes |
| ledger-transfers | 2 | `unchanged` | failed | 2m 09s | yes (the starter's) |
| library-loans | 1 | `inconclusive` | failed | 24s | no |
| library-loans | 2 | `budget_exhausted` | **passed**, 11 of 11 | 60m 03s | no |
| room-bookings | 1 | `budget_exhausted` | failed, 8 of 9 | 60m 03s | no |
| room-bookings | 2 | `verified` | **passed**, 9 of 9 | 38m 39s | yes |
| todo-deps | 1 | `inconclusive` | failed | 1m 21s | no |
| todo-deps | 2 | `inconclusive` | failed | 33m 10s | no |

## What the results say

- **Every run stopped on time.** The two runs that used the whole budget
  took 3,602.9 and 3,603.1 seconds. In both, the model call that was
  running at the deadline was cut to the time left (the log shows
  "timed out after 52.0 seconds" and "after 5.0 seconds"), so neither
  went past 60 minutes by more than a few seconds.
- **The budget lost no work that Certo could have checked.** One run
  ended `budget_exhausted` with work that passes the hidden tests
  (`library-loans` repeat 2). Its project had no tests: the agent's last
  steps were `go vet ./...` (clean) and `go test ./...`, which printed
  `[no test files]`. With nothing to run, Certo can't say `verified`,
  and had the run finished on time the verdict would have been
  `inconclusive`. More time doesn't fix that; tests do. The other run
  that used its hour (`room-bookings` repeat 1) had no tests either, and
  its work fails one hidden test.
- **Twice the time didn't solve more tasks.** Half the runs ended in
  minutes, or in `todo-deps` repeat 2 after 33, because `qwen3.8` wrote
  a tool call as plain text instead of making it (see
  [Troubleshooting](../troubleshooting.md#the-run-ends-at-once-with-a-tool-call-as-the-agents-last-message)),
  and the run ended there. That happened once in the 30-minute
  benchmark. With so few runs, the difference can be chance, but here it
  decided more results than the budget did.
- **One model call waited 20 minutes.** In `room-bookings` repeat 1, a
  call timed out after 1,200 seconds, a third of the run's hour. A slow
  local model spends a large part of any budget waiting.
- **The fooled run left out the feature.** In `ledger-transfers`
  repeat 1, the agent fixed the two bugs but never added
  `ledger/transfers.py`, which the task asks for. The project's 33 tests
  passed, so Certo said `verified`; the hidden tests failed at import.
  This isn't about time: Certo's checks only see the tests the project
  has.
- **Small sample:** 8 runs, two per task, one model.

## What this means

- **The time budget does its job:** runs stop on time, and the only
  right work it stopped was work Certo couldn't check anyway.
- **For `qwen3.8` on these tasks, the limits are tests and tool calls,
  not time.** Getting the model to write tests for new features, and
  handling tool calls written as text, would turn more of these runs
  into `verified` than a longer budget does.
- **A longer default budget for local models isn't shown to help** by
  this run. `max_task_seconds` stays a per-arm and per-run choice.

## Reproduce it

Enable `qwen3.8-27b-local` (`ollama/qwen3.8:27b`) in your `models.yaml`,
then:

```bash
certo bench --config docs/benchmark/bench-0.1.25-budget.yaml
```

It takes up to 8 hours on a setup like this one: 8 runs, one at a time,
each with up to 60 minutes.
