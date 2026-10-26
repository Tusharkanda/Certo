# Benchmark: condensing on a local model at 32K, Certo 0.1.25

One `certo bench` run on the four larger tasks of task set version 2,
with `qwen3.8:27b` on Ollama and a 32,768-token context window. It
compares two arms that differ in one setting: condensing on (the
default) and off (`condense: false`). It answers one question: when a
long run fills a small context window, does summarizing the older steps
help the local model finish?

## The setup

- **Certo:** 0.1.25 (unreleased, `d7d6951`). **Task set:** version 2
  (`6ed42dae4bca`, bundled), its four larger tasks: `ledger-transfers`
  (Python), `library-loans` (Go), `room-bookings` (Node and React) and
  `todo-deps` (Rust).
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Local model:** `ollama/qwen3.8:27b`, on Ollama 0.40.6 on another
  machine. Both arms ask Ollama for a 32,768-token window with every
  request (`context_tokens: 32768`), so condensing starts at 24,576
  tokens, a quarter of the window being kept for the answer.
- **Run:** 2026-10-25, from 17:39 UTC, one run at a time. 2 repeats, so
  8 runs per arm. Every run had the default 30-minute time budget.
- **File:** [bench-0.1.25-context.yaml](bench-0.1.25-context.yaml).
  **Results folder:** `bench-results/context-0.1.25`, on the machine that
  ran it.

| Arm | Strategy | Model | Condensing |
|---|---|---|---|
| `qwen-32k` | single | `qwen3.8-27b-local` | on (default) |
| `qwen-32k-no-condense` | single | `qwen3.8-27b-local` | off |

## Results

| Arm | Hidden tests passed | Verified | Fooled | Median time |
|---|---|---|---|---|
| `qwen-32k` | 3/8 | 3/8 | 1 | 30m 06s |
| `qwen-32k-no-condense` | 0/8 | 0/8 | 0 | 30m 04s |

Both arms cost nothing: the model runs locally.

Per run (verdict, hidden tests, how often older steps were summarized):

| Task | Repeat | `qwen-32k` | `qwen-32k-no-condense` |
|---|---|---|---|
| ledger-transfers | 1 | `verified`, **passed**, 2 summaries | `budget_exhausted`, failed |
| ledger-transfers | 2 | `budget_exhausted`, failed | `budget_exhausted`, failed |
| library-loans | 1 | `budget_exhausted`, **passed**, 1 summary | `budget_exhausted`, failed |
| library-loans | 2 | `budget_exhausted`, failed | `budget_exhausted`, failed |
| room-bookings | 1 | `verified`, failed (fooled, see below) | `retry_exhausted`, failed |
| room-bookings | 2 | `verified`, **passed** | `budget_exhausted`, failed |
| todo-deps | 1 | `budget_exhausted`, failed | `budget_exhausted`, failed |
| todo-deps | 2 | `inconclusive`, failed | `inconclusive`, failed |

13 of the 16 runs used their whole 30 minutes. The longest took 30m 43s,
so no run went past its budget by more than one model call.

## What the results say

- **Condensing kept long runs going.** Two runs with condensing filled
  the window: one summarized twice and one once. Both went on and wrote
  work that passes the hidden tests. Without condensing, three runs grew
  past the point where condensing would have started, and none passed.
  `ledger-transfers` was never solved in the 0.1.23 baseline (0 of 3,
  with a 131,072-token window); with condensing at 32K, one of two runs
  solved it.
- **Most runs never filled the window.** In the other runs the
  conversation stayed under 24,576 tokens, so both arms ran exactly the
  same way. What limited them was speed: a run that used its whole
  budget made between 4 and 41 model calls in those 30 minutes. So part
  of the gap between the arms, such as the `room-bookings` results, is
  chance in a small sample, not condensing.
- **Both `todo-deps` repeat 2 runs ended within minutes,** because
  `qwen3.8` wrote its first tool call as plain text instead of making it
  (see
  [Troubleshooting](../troubleshooting.md#the-run-ends-at-once-with-a-tool-call-as-the-agents-last-message)).
  The project was left unchanged and Certo said `inconclusive`.
- **One run fooled Certo, from a bug that's now fixed.** In
  `room-bookings` repeat 1, the agent wrote no tests. The time budget ran
  out, Certo ran the project's checks once, and `npm test`, finding no
  tests, passed. The fix
  ([a Node project with no tests is no longer `verified`](../launch/release-notes-v0.1.25.md))
  landed after this benchmark started. Run on the saved project, today's
  checks say `inconclusive`. They say the same for `room-bookings`
  repeat 2, which also has no tests, so with today's code that run would
  count as an unconfirmed pass, not as `verified`.
- **Small sample:** 8 runs per arm, two per task.

## What this means

- **Keep condensing on (the default) when a local model's window is
  small.** It only acts when the window fills, and here every run that
  got there and went on was a run that passed.
- **At 32K, the window isn't the main limit for `qwen3.8` on these
  tasks: time is.** Most runs ended `budget_exhausted` well before the
  window filled. A longer time budget is what would show more.

## Reproduce it

Enable `qwen3.8-27b-local` (`ollama/qwen3.8:27b`) in your `models.yaml`,
then:

```bash
certo bench --config docs/benchmark/bench-0.1.25-context.yaml
```

It takes about 8 hours on a setup like this one: 16 runs, one at a time,
most of them using their whole 30 minutes.
