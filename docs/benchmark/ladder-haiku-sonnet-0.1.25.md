# Benchmark: the Haiku → Sonnet ladder in Certo 0.1.25

One `certo bench` run on the 13 bundled tasks, comparing the README's
cheap-cloud-first ladder with each of its two models alone
([#24](https://github.com/alessioricco/certo/issues/24)). It answers one
question: does starting on `claude-haiku-5-5` and moving to
`claude-sonnet-5-5` only when Haiku can't finish cost less than Sonnet
alone, without solving less?

## The setup

- **Certo:** 0.1.25 (unreleased, `80e46df`). **Task set:** version 2
  (`6ed42dae4bca`, bundled), 13 tasks: Python, Node, Go and Rust.
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Run:** 2026-10-25, from 20:09 UTC, three runs at a time.
  1 repeat, so 13 runs per arm. The file asks for 3 repeats; the run was
  stopped after the first, as planned, because no arm failed a task (see
  [What this means](#what-this-means)).
- **File:** [bench-0.1.25-ladder.yaml](bench-0.1.25-ladder.yaml).
  **Results folder:** `bench-results/ladder-0.1.25`, on the machine that
  ran it.

| Arm | Strategy | Models |
|---|---|---|
| `haiku` | single | `anthropic/claude-haiku-5-5` |
| `sonnet` | single | `anthropic/claude-sonnet-5-5` |
| `haiku-then-sonnet` | escalate | `claude-haiku-5-5`, then `claude-sonnet-5-5` |

One difference from the README's `cheap-first` ladder: there Haiku gets
one fix attempt (`retries: 1`); a benchmark arm can't set that per model,
so every rung had the default two. No run needed a fix attempt, so it
made no difference here.

## Results

| Arm | Hidden tests passed | Verified | Fooled | Median time | Cost | Cost per solved task |
|---|---|---|---|---|---|---|
| `haiku` | 13/13 | 13/13 | 0 | 56s | $0.27 | $0.020 |
| `sonnet` | 13/13 | 13/13 | 0 | 39s | $2.76 | $0.212 |
| `haiku-then-sonnet` | 13/13 | 13/13 | 0 | 55s | $0.26 | $0.020 |

Total for the three arms: **$3.29**. Every run was `verified` with its
hidden tests passing, no run needed a fix attempt, and no run fooled
Certo (`verified` with failing hidden tests).

**The ladder never climbed.** Haiku finished every task on the first
rung, so the ladder arm is Haiku alone: the same results at the same
cost (the $0.001 difference is run-to-run variation). Sonnet alone cost
about **10 times as much** for the same 13 passes. It was faster: its
median run took 39s against Haiku's 56s, and on the four larger tasks
(`ledger-transfers`, `library-loans`, `room-bookings`, `todo-deps`) about
2 to 3 minutes against Haiku's 3 to 4.

Per task, time and cost:

| Task | `haiku` | `sonnet` | `haiku-then-sonnet` |
|---|---|---|---|
| duration-parser | 40s, $0.008 | 29s, $0.103 | 55s, $0.010 |
| inventory-fix | 56s, $0.012 | 39s, $0.140 | 55s, $0.010 |
| ledger-transfers | 3m 57s, $0.039 | 2m 14s, $0.319 | 2m 26s, $0.030 |
| library-loans | 4m 05s, $0.047 | 2m 36s, $0.425 | 5m 24s, $0.063 |
| page-ranges | 44s, $0.009 | 35s, $0.114 | 1m 06s, $0.010 |
| pedestrian-crossing | 54s, $0.009 | 30s, $0.105 | 55s, $0.010 |
| room-bookings | 3m 15s, $0.040 | 2m 41s, $0.402 | 2m 30s, $0.031 |
| semver-order | 1m 07s, $0.014 | 53s, $0.153 | 50s, $0.011 |
| slugify | 24s, $0.006 | 29s, $0.105 | 27s, $0.006 |
| temperature-table | 34s, $0.007 | 25s, $0.095 | 33s, $0.007 |
| todo-deps | 4m 18s, $0.053 | 3m 04s, $0.538 | 4m 33s, $0.058 |
| token-bucket | 1m 19s, $0.015 | 39s, $0.136 | 41s, $0.009 |
| wordle-score | 42s, $0.008 | 39s, $0.127 | 53s, $0.010 |

## What this means

- **On tasks like these, the ladder costs what Haiku costs.** It only
  adds Sonnet's price when Haiku fails, and here Haiku never did.
- **This run can't show the ladder paying off.** A ladder earns its keep
  on a task the cheap model fails and the strong one solves; task set v2
  has none for these two models (the 0.1.23 baseline found the same:
  every cloud model passed 13 of 13). Two more repeats of the same tasks
  would most likely repeat this result, so they weren't run. What would
  show it is harder tasks, where Haiku sometimes fails.
- **Small sample:** 13 runs per arm, one each per task.

## Reproduce it

Enable `claude-haiku-5-5` and `claude-sonnet-5-5` in your `models.yaml`,
then:

```bash
certo bench --config docs/benchmark/bench-0.1.25-ladder.yaml --parallel 3 --max-cost 20
```

The plan printed before the run estimated at most ~$117 for all three
repeats: it prices every run at about 500,000 input tokens, far more than
these runs used. `--max-cost` stops starting new runs once the real cost
reaches the limit.
