# Benchmark baseline: Certo 0.1.23

Two `certo bench` runs on the 13 bundled tasks of task set version 2:
`qwen3.8:27b`, the local model `certo init` suggests, three times each,
and the same three cloud models as in 0.1.22, once each. Every model ran
alone. It is the first baseline on the four larger tasks, and checks that
0.1.23 didn't make results worse on the nine small ones. How the
benchmark works, and what each column means, is in
[Benchmark models and strategies](../guides/benchmark.md). The previous
baseline is [0.1.22](baseline-0.1.22.md).

## The setup

- **Certo:** 0.1.23 (not released yet), from a source checkout.
  **Task set:** version 2 (`9361a65d7dbb`, bundled), 13 tasks: the 9
  small ones of version 1 (6 Python, 3 Node) and 4 larger ones, each in
  its own language: `ledger-transfers` (fix two bugs in an existing
  Python package), `todo-deps` (a Rust command-line program),
  `library-loans` (a Go HTTP API) and `room-bookings` (a Node API and a
  React page).
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Local model:** on Ollama 0.40.6, on another machine, with a context
  length of 131,072 tokens and Q4_K_M quantization (read from Ollama's
  `/api/version` and `/api/ps`; no other model was loaded when the local
  run started): the same setup as 0.1.22. Each model call could take up
  to 1200 seconds.
- **Cloud run:** 2026-10-23, from 21:23 UTC. 1 repeat, so 13 runs per
  model, three runs at a time (`--parallel 3`). Each model ran at
  reasoning effort `high`, from the model list. 38 of the 39 runs had
  finished by 21:48; the last one, a `luna` run, ended at 00:33 (see
  [The 2h53m run](#the-2h53m-run)).
- **Local run:** 2026-10-24, 00:33 to 11:33 UTC. 3 repeats, so 39 runs.
- **Results folders:** `bench-results/0.1.23-cloud` and
  `bench-results/0.1.23-local`, on the machine that ran them.

| Arm | Model |
|---|---|
| `qwen3.8` | `ollama/qwen3.8:27b` |
| `haiku` | `anthropic/claude-haiku-5-5` |
| `luna` | `openai/gpt-6-luna` |
| `sonnet` | `anthropic/claude-sonnet-5-5` |

## Results

| Arm | Hidden tests passed | Verified | Fooled | Caught | Unconfirmed passes | Median time | Cost per solved task |
|---|---|---|---|---|---|---|---|
| `sonnet` | 13/13 | 13/13 | 0 | 0 | 0 | 40s | $0.19 |
| `haiku` | 13/13 | 13/13 | 0 | 0 | 0 | 1m 05s | $0.020 |
| `luna` | 13/13 | 13/13 | 0 | 0 | 0 | 1m 12s | $0.013 |
| `qwen3.8` | 32/39 | 31/39 | 0 | 6 | 1 | 8m 49s | $0.00 |

Total cost: **$2.96**, all of it the cloud run (sonnet $2.53, haiku
$0.26, luna $0.17). The plan had estimated at most ~$21.00. No run
stopped with an error, and no cloud run needed a fix attempt.

Hidden tests passed, per task (local out of 3, cloud out of 1):

| Task | `qwen3.8` | `haiku` | `luna` | `sonnet` |
|---|---|---|---|---|
| duration-parser | **2** | 1 | 1 | 1 |
| inventory-fix | 3 | 1 | 1 | 1 |
| page-ranges | 3 | 1 | 1 | 1 |
| pedestrian-crossing | 3 | 1 | 1 | 1 |
| semver-order | 3 | 1 | 1 | 1 |
| slugify | 3 | 1 | 1 | 1 |
| temperature-table | 3 | 1 | 1 | 1 |
| token-bucket | **2** | 1 | 1 | 1 |
| wordle-score | 3 | 1 | 1 | 1 |
| ledger-transfers | **0** | 1 | 1 | 1 |
| library-loans | 3 | 1 | 1 | 1 |
| room-bookings | 3 | 1 | 1 | 1 |
| todo-deps | **1** | 1 | 1 | 1 |

The larger tasks take longer. The median `sonnet` run took 39s on the
small tasks and 2m 23s on the larger ones; `qwen3.8`, 6m 57s and
31m 13s.

## What the results say

- **Certo was not fooled once in 78 runs.** Every one of its 70
  `verified` verdicts was right. The 7 runs whose hidden tests failed
  all ended without `verified`.
- **The cloud models solved every task, larger ones included.** The
  four larger tasks don't separate them yet: like the nine small ones,
  they show that nothing broke.
- **`qwen3.8` solved two of the four larger tasks every time**
  (`library-loans` in Go, `room-bookings` in Node and React), one of
  three times on `todo-deps` in Rust, and never `ledger-transfers`.
- **Most local failures were tool calls written as text, not wrong
  code.** In 6 of the 7 failed local runs, and in the one unconfirmed
  pass, `qwen3.8` wrote a tool call as plain text instead of making it,
  which ends its turn; Certo then reported what the folder held. It
  happened in 7 of 39 runs, against 1 of 27 in 0.1.22 (see
  [Tool calls written as text](#tool-calls-written-as-text)).
- **The time budget doesn't hold a slow local model.** Two `todo-deps`
  runs took 46 and 83 minutes against a 30-minute budget, because Certo
  checks it between runs, not during one; one step of the agent took up
  to 21 minutes.

## Compared with 0.1.22

On the nine small tasks, the ones both baselines share:

| Arm | 0.1.22 | 0.1.23 |
|---|---|---|
| `sonnet` | 9/9, 34s, $1.07 | 9/9, 39s, $1.08 |
| `haiku` | 9/9, 51s, $0.09 | 9/9, 47s, $0.09 |
| `luna` | 9/9, 54s, $0.05 | 9/9, 1m 03s, $0.05 |
| `qwen3.8` | 26/27, 1 fooled, 5m 44s | 25/27, 0 fooled, 6m 57s |

No sign that 0.1.23 made results worse: the cloud models are unchanged,
and one run fewer for `qwen3.8` is within chance. Its input tokens on
these tasks were the same as in 0.1.22 (4.0 million). The local run used
the same Ollama setup as 0.1.22 (version, context length, quantization
and call timeout), so its times compare; the cloud runs both ran three at
a time.

## Tool calls written as text

Some local models, on some Ollama setups, sometimes write a tool call as
text in their answer instead of making it. The SDK then sees an answer
with no action, and the agent's turn ends. Certo can only check what the
folder holds at that point. In this run:

| Run | When | Verdict | Hidden tests |
|---|---|---|---|
| `ledger-transfers` · 1, 2, 3 | after reading the package's files, each time | `unchanged` | failed |
| `duration-parser` · 2 | its first step | `inconclusive` (empty folder) | failed |
| `token-bucket` · 3 | its first step | `unchanged` | failed |
| `pedestrian-crossing` · 2 | after writing the code, when writing its tests | `inconclusive` | passed |
| `todo-deps` · 2 | its last step, after 83 minutes | `budget_exhausted` | failed |

In every case Certo's verdict matched what was there: no change, no
tests, or code that wasn't finished. With `--escalate`, these runs would
have gone to the next model.

Why it happened more often than in 0.1.22 is not known. On Certo's side
nothing that reaches the model changed: the system prompt was identical
apart from the date, and the SDK and LiteLLM versions were the same.
Ollama's version and settings were the same too; the model's exact
build wasn't recorded in 0.1.22, so it can't be compared. 7 of 39
against 1 of 27 may partly be chance. `ledger-transfers` did it in all
three runs, each time after reading several files of the package at
once.

## The 2h53m run

The `luna` run of `todo-deps` passed, but took 2 hours 53 minutes; the
other 38 cloud runs took at most 6 minutes each. To try its program, the
agent ran a shell command that ended with `exit`, which closed the
terminal session, so the command never returned. It then asked to wait
for more output with a time limit of `10000`, apparently meaning
milliseconds; the terminal tool counts seconds, so it waited 10,000
seconds (2h47m). Afterwards it finished the task normally, and the hidden
tests passed.

Certo doesn't limit how long one tool call may wait, and checks its time
budget only between runs, so nothing stopped it. Only the benchmark's
total time suffered: the run cost $0.04.

## The unconfirmed pass

- **`pedestrian-crossing` · repeat 2** (`inconclusive`). The agent wrote
  `crossing.py`, then wrote the call that would create its test file as
  text, which ended its turn. With no tests, nothing could show the code
  right or wrong, so Certo said `inconclusive`. The code was right: the
  hidden tests passed.

## Reproduce this run

The two benchmark files are
[bench-0.1.23-local.yaml](bench-0.1.23-local.yaml) and
[bench-0.1.23-cloud.yaml](bench-0.1.23-cloud.yaml). Copy them, enable
their models in your `models.yaml`, and run:

```bash
certo bench --config bench-0.1.23-cloud.yaml --parallel 3
certo bench --config bench-0.1.23-local.yaml
```

The Go, Rust and Node tasks need `go`, `cargo` and `npm`, and
`room-bookings` needs the network for `npm ci`. Expect about 25 minutes
for the cloud run and 11 hours for the local one with the model on a
separate machine. The local run can be split over several sessions: stop
it, then continue it with the same `--out` and `--resume`. Your numbers
will differ: models vary between runs, and local times depend on the
machine serving the model.

## Limits of this baseline

- The cloud models solved all 13 tasks, so the tasks can't tell them
  apart.
- One repeat for the cloud models: 13 runs each, and one run per larger
  task.
- One local model and one Ollama setup.
- Single-model arms only: escalation wasn't measured here. It is in
  [Escalation in 0.1.17](escalation-0.1.17.md).

## Related

- [Baseline 0.1.22](baseline-0.1.22.md)
- [Choose a local model](../guides/choose-a-local-model.md)
- [Benchmark models and strategies](../guides/benchmark.md)
- [Ollama and local models](../guides/ollama-and-local-models.md)
