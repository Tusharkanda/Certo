# Benchmark: tool-call reminders, Certo 0.1.26

Two `certo bench` runs on task set version 2. They answer one question:
when a local model writes a tool call as plain text instead of making
it, does Certo's reminder (`CERTO_TOOL_CALL_REMINDERS`) get the run
going again, and does it leave a cloud model alone?

## The setup

- **Certo:** 0.1.26 (unreleased, with the reminder of `6c10d29`).
  **Task set:** version 2 (`6ed42dae4bca`, bundled).
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Local run:** `ollama/qwen3.8:27b`, on Ollama 0.40.6 on another
  machine, with a 32,768-token window (`context_tokens: 32768`). The two
  tasks where the saved runs showed it most: `todo-deps` (Rust) and
  `ledger-transfers` (Python). 3 repeats, so 6 runs per arm, one at a
  time, on 2026-10-27 from 09:48 to 14:25 UTC. Every run had the default
  30-minute time budget. The model's build was not recorded: that
  started with a later change.
  **File:** [bench-0.1.26-reminders-local.yaml](bench-0.1.26-reminders-local.yaml).
- **Cloud run:** `anthropic/claude-haiku-5-5`, with the default (3
  reminders), on all 13 tasks, once, on 2026-10-27 from 09:28 to
  09:37 UTC.
  **File:** [bench-0.1.26-reminders-cloud.yaml](bench-0.1.26-reminders-cloud.yaml).
- **Results folders:** `bench-results/reminders-0.1.26-local` and
  `bench-results/reminders-0.1.26-cloud`, on the machine that ran them.
  Reminders were counted from the saved conversations.

| Arm | Strategy | Model | Reminders |
|---|---|---|---|
| `qwen-no-reminders` | single | `qwen3.8-27b-local` | off (`tool_call_reminders: 0`) |
| `qwen-reminders` | single | `qwen3.8-27b-local` | up to 3 (default) |
| `haiku-reminders` | single | `claude-haiku-5-5` | up to 3 (default) |

## Results

| Arm | Hidden tests passed | Verified | Fooled | Runs with a tool call as text | Reminders sent | Median time | Cost |
|---|---|---|---|---|---|---|---|
| `qwen-no-reminders` | 0/6 | 1/6 | 1 | 2 | 0 | 30m 06s | $0.00 |
| `qwen-reminders` | 0/6 | 1/6 | 1 | 2 | 6 | 30m 07s | $0.00 |
| `haiku-reminders` | 13/13 | 13/13 | 0 | 0 | 0 | 1m 07s | $0.30 |

Per local run (verdict, hidden tests, time):

| Task | Repeat | `qwen-no-reminders` | `qwen-reminders` |
|---|---|---|---|
| todo-deps | 1 | `inconclusive`, failed, 5m 01s, tool call as text | `inconclusive`, failed, 20m 59s, tool call as text, 3 reminders |
| todo-deps | 2 | `budget_exhausted`, failed | `inconclusive`, failed, 8m 11s, tool call as text, 3 reminders |
| todo-deps | 3 | `inconclusive`, failed, 34s, tool call as text | `budget_exhausted`, failed |
| ledger-transfers | 1 | `budget_exhausted`, failed | `verified`, failed (fooled) |
| ledger-transfers | 2 | `budget_exhausted`, failed | `budget_exhausted`, failed |
| ledger-transfers | 3 | `verified`, failed (fooled) | `budget_exhausted`, failed |

## What the results say

- **The reminder didn't save a run.** `qwen3.8` wrote a tool call as
  text in 2 of 6 runs in each arm, all on `todo-deps`, each time as its
  first or second step. Without reminders, those runs ended at once.
  With them, each run got all 3 reminders. After 4 of the 6 reminders
  the model made one real tool call (it looked at the project), then
  went back to writing the next call as text. It never got further than
  reading files, so both runs still ended `inconclusive`, with the
  project unchanged, only later: in 21 and 8 minutes instead of 5
  minutes and 34 seconds.
- **The model, not the conversation, decides it.** Once `qwen3.8`
  started writing calls as text in a run, it kept doing it. In the runs
  where its first call was real, it never wrote one as text.
- **The cloud model got no reminder.** `claude-haiku-5-5` made real tool
  calls in every run, so it was sent none, and it passed all 13 tasks,
  as in the [0.1.23 baseline](baseline-0.1.23.md).
- **The rest of the gap is time.** 7 of the 12 local runs used their
  whole 30 minutes, and the two runs Certo called `verified` failed the
  hidden tests (one error, and 1 of 27 tests failed). That is the same
  as without reminders, as in the
  [condensing benchmark](context-0.1.25.md).
- **Small sample:** 6 local runs per arm, 3 per task.

## What this means

- **The reminder stays on by default.** It costs a cloud model nothing,
  and the conversation shows what happened.
- **It doesn't fix a local model that writes tool calls as text.** It
  only turns an instant `inconclusive` into a later one. When a model
  does this, the fix is still another model, a newer Ollama, or
  `CERTO_TOOL_CALL_REMINDERS=0` to end those runs at once. Why
  `qwen3.8` does it in some runs and not others is still open.

## Reproduce it

Enable `qwen3.8-27b-local` (`ollama/qwen3.8:27b`) and `claude-haiku-5-5`
in your `models.yaml`, then:

```bash
certo bench --config docs/benchmark/bench-0.1.26-reminders-local.yaml
certo bench --config docs/benchmark/bench-0.1.26-reminders-cloud.yaml
```

The local file takes about 5 hours on a setup like this one, the cloud
file about 10 minutes and $0.30.
