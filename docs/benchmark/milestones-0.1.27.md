# Benchmark: milestone mode on a local model, Certo 0.1.27

One `certo bench` run. It asks one question: on a task the size of a
small app, does a local model do better when Certo runs the task in
milestones, one at a time, than when it gets the whole task at once?

Each arm has the same model and the same total time: 100 minutes for
the whole task, or 20 minutes for each of the five milestones.

## The setup

- **Certo:** 0.1.27 (not released yet).
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Task `spreadsheet`** (task set `apps-1`, `5b5cd2015e1e`, in
  `app-tasks/`): a spreadsheet engine in one Python file, in five
  milestones: numbers and arithmetic, references, ranges and functions,
  errors, then CSV files and a command line. 111 hidden tests, named
  by milestone: 37, 6, 26, 29 and 13.
- **Model:** `ollama/qwen3.8:27b` (build `aaee06c39dcf`), on Ollama
  0.40.6 on another machine, with a 32,768-token window
  (`context_tokens: 32768`).
- **Arms:** `qwen-whole` gets the whole task at once, with
  `max_task_seconds: 6000`. `qwen-milestones` gets it in milestones
  (`milestones: true`), with `max_task_seconds: 1200` for each one.
  3 repeats per arm, one run at a time, on 2026-10-29 from 18:54 to
  2026-10-30 00:37 UTC.
  **File:** [bench-0.1.27-milestones-local.yaml](bench-0.1.27-milestones-local.yaml).
- **Cloud check of the task:** one run each of
  `anthropic/claude-haiku-5-5` and `anthropic/claude-sonnet-5-5`, the
  whole task at once, on 2026-10-29 at 18:01 UTC.
  **File:** [bench-0.1.27-spreadsheet-calibrate.yaml](bench-0.1.27-spreadsheet-calibrate.yaml).
- **Results folders:** `bench-results/milestones-local-0.1.27` and
  `bench-results/spreadsheet-calibrate`, on the machine that ran them.
  The local run started before Certo counted hidden tests per
  milestone, so its saved projects were graded again afterwards with
  `scripts/regrade_bench.py`. No run's pass or fail changed.

## Results

| Arm | Hidden tests passed | Verified | Median time | Tokens out | Cost |
|---|---|---|---|---|---|
| `qwen-whole` | 0/3 | 0/3 | 81m 21s | 279,656 | $0.00 |
| `qwen-milestones` | 0/3 | 0/3 | 33m 03s | 114,741 | $0.00 |
| `haiku-whole` (cloud check) | 1/1 | 1/1 | 6m 40s | 73,463 | $0.06 |
| `sonnet-whole` (cloud check) | 1/1 | 1/1 | 3m 18s | 30,378 | $0.48 |

Hidden tests passed per milestone, the three local runs added up:

| Arm | Milestone 1 | Milestone 2 | Milestone 3 | Milestone 4 | Milestone 5 |
|---|---|---|---|---|---|
| `qwen-whole` | 0/111 | 0/18 | 0/78 | 0/87 | 0/39 |
| `qwen-milestones` | 108/111 | 0/18 | 0/78 | 0/87 | 3/39 |

`qwen-whole` wrote no file, so its hidden tests couldn't even load
`sheet.py`; the table counts every one as failed.

Per local run (verdict, how far it got, time):

| Repeat | `qwen-whole` | `qwen-milestones` |
|---|---|---|
| 1 | `stuck`, no file, 78m 04s | milestone 1 `verified`, milestone 2 `budget_exhausted`, 33m 03s |
| 2 | `stuck`, no file, 91m 22s | milestone 1 `budget_exhausted`, 20m 02s |
| 3 | `stuck`, no file, 81m 21s | milestone 1 `verified`, milestone 2 `budget_exhausted`, 38m 24s |

## What the results say

- **Neither arm finished the task.** The goal of milestone mode, an
  app-sized task ending `verified` on a local model, is not reached
  yet.
- **With the whole task, qwen3.8 never started.** In all three runs,
  most replies took 12 to 30 minutes and 10,000 to 20,000 output
  tokens, and came back empty: no text and no tool call. After a few empty replies
  the run was `stuck`. In 80 to 90 minutes each run made two to four
  tool calls (a listing, a plan) and wrote no file. The likely cause is
  the model's reasoning filling the 32,768-token window before it
  answers; this run doesn't prove it.
- **In milestones, qwen3.8 built milestone 1.** All three runs wrote a
  `sheet.py` that passed 36 of the 37 milestone 1 hidden tests, and two
  of them were `verified` in 13 and 18 minutes. The third wrote its
  `sheet.py` at the 20-minute limit, so Certo said `budget_exhausted`
  and stopped there. The one failing test is the same in all three:
  `" =1+2"` (a space, then `=`) must be text, because the task says a
  formula starts with `=`; the runs read it as a formula.
- **Milestone 2 ran out of time with no edit.** In both runs that got
  there, the agent spent its 20 minutes reading `sheet.py` and its
  tests and planning, with most replies taking 3 to 6 minutes, and
  changed no file. Certo said `budget_exhausted`, and the run stopped, as
  milestone mode does when a milestone isn't `verified`.
- **The 3 milestone 5 hidden tests that passed** (one per run) only
  are all the same one: the program exits when its input ends. They
  say nothing about milestone 5.
- **The task doesn't separate cloud models.** Haiku and Sonnet both
  passed all 111 hidden tests in one go, in 7 and 3 minutes. On this
  task, milestones can only help a local model.

## What to try next

- Run the milestone arm with more time per milestone, or
  `--resume` the runs that stopped, to see whether milestone 2 gets
  done when it has longer. Each reply on milestone 2 took minutes, so
  20 minutes was only a few steps.
- Find out why the whole-task replies came back empty, for example
  with a larger `context_tokens`, before comparing the arms again.

## Related

- [The second run, with a 65,536-token window](milestones-64k-0.1.27.md)
- [Run a task in milestones](../guides/run-in-milestones.md)
- [The first live milestone runs](milestones-live-0.1.27.md): the same
  feature on Haiku, with the task files used
- [The benchmark guide](../guides/benchmark.md)
