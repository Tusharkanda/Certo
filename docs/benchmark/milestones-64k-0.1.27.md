# Benchmark: milestone mode on a local model with a larger window, Certo 0.1.27

The second run of [milestone mode on a local model](milestones-0.1.27.md),
with two changes after the first: a context window of 65,536 tokens
instead of 32,768, and 40 minutes for each milestone instead of 20. The
whole task in one go keeps its 100 minutes.

## The setup

- **Certo:** 0.1.27 (not released yet).
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Task `spreadsheet`** (task set `apps-1`, `5b5cd2015e1e`): the same
  as in the first run, with 111 hidden tests: 37, 6, 26, 29 and 13 for
  milestones 1 to 5.
- **Model:** `ollama/qwen3.8:27b` (build `aaee06c39dcf`), on Ollama
  0.40.6 on another machine, with a 65,536-token window
  (`context_tokens: 65536`) and a 1,200-second limit on each model call.
- **Arms:** `qwen-whole-64k` gets the whole task at once, with
  `max_task_seconds: 6000`. `qwen-milestones-64k` gets it in milestones
  (`milestones: true`), with `max_task_seconds: 2400` for each one.
  3 repeats per arm, one run at a time, on 2026-10-30 from 07:06 to
  20:13 UTC.
  **File:** [bench-0.1.27-milestones-local-64k.yaml](bench-0.1.27-milestones-local-64k.yaml).
- **Results folder:** `bench-results/milestones-local-64k-0.1.27`, on
  the machine that ran it. The Ollama machine shut down during the
  second repeat; those four runs failed at once on the network, were
  deleted, and were run again with `--resume` when it was back.

## Results

| Arm | Hidden tests passed (all 111) | Verified | Hidden tests passed, all runs | Median time | Tokens out |
|---|---|---|---|---|---|
| `qwen-whole-64k` | 0/3 | 0/3 | 187/333 | 100m 06s | 245,765 |
| `qwen-milestones-64k` | 0/3 | 0/3 | 85/333 | 77m 38s | 239,324 |

Per run (how far it got, hidden tests passed):

| Repeat | `qwen-whole-64k` | `qwen-milestones-64k` |
|---|---|---|
| 1 | no `sheet.py`, 0/111 | milestones 1 and 2 `verified`, out of time on 3; 43/111 |
| 2 | `sheet.py` written at minute 94, no tests; 87/111 | milestones 1 and 2 `verified`, out of time on 3; 42/111 |
| 3 | `sheet.py` written at minute 96, no tests; 100/111 | out of time on milestone 1, no file; 0/111 |

Every run ended `budget_exhausted`. The two whole-task runs that wrote
`sheet.py` wrote no tests, so Certo had nothing to run and couldn't
say `verified`.

Hidden tests passed per milestone, over the three runs of each arm (a
run with no `sheet.py` counts as 0):

| Arm | Milestone 1 | Milestone 2 | Milestone 3 | Milestone 4 | Milestone 5 |
|---|---|---|---|---|---|
| `qwen-whole-64k` | 71/111 | 4/18 | 45/78 | 48/87 | 19/39 |
| `qwen-milestones-64k` | 73/111 | 10/18 | 0/78 | 0/87 | 2/39 |

## What the results say

- **The larger window made the one-go arm work.** At 32,768 tokens
  every reply was empty and no run wrote a file. At 65,536, two of
  three runs wrote the whole engine (595 lines in one case) in a
  single step near the end, passing 87 and 100 of the 111 hidden tests.
  The model thinks through the whole program first: these runs made
  only 3 to 7 tool calls in 100 minutes.
- **Milestone mode got the first milestones verified, but less done.**
  Two runs had milestones 1 and 2 `verified`, which no run reached in
  the first benchmark, and one run passed all 37 milestone 1 hidden
  tests. Then milestone 3 ran out of its 40 minutes with no edit. In
  total the milestone arm passed fewer hidden tests (85 against 187),
  but what it passed was checked by its own tests along the way.
- **The time goes to planning at the start of a milestone.** Once the
  model is editing and testing, its steps take 10 to 40 seconds. At the
  start of a milestone, in a fresh conversation, it reads the files
  quickly, then its next replies took 5 to 25 minutes each while it
  planned. On milestone 3, that used up the 40 minutes in both runs.
  The run that failed milestone 1 spent 25 minutes on one reply.
- **Seven model calls hit the 1,200-second limit on one call** and were
  sent again, so that thinking was lost.
- **The milestone 2 hidden test that both milestone runs failed** builds
  a chain of 200 cells, each one adding 1 to the cell above it. Their
  `sheet.py` follows references by recursion and hit Python's recursion
  limit. The task doesn't name a size, so this test is stricter than
  the task text.

## What to try next

- Keep more of the conversation across milestones, or start each new
  milestone with a short summary of the code, so the model doesn't
  spend its first replies reading and planning again from nothing.
- A longer limit on one model call for this model, so long replies
  aren't thrown away and sent again.
- Ask for tests earlier in the one-go task, so a run like repeat 3
  (100 of 111 hidden tests) can end `verified`.

## Related

- [The first run, at 32,768 tokens](milestones-0.1.27.md)
- [The third run, with a handover between milestones](milestones-handover-0.1.27.md)
- [Run a task in milestones](../guides/run-in-milestones.md)
- [The benchmark guide](../guides/benchmark.md)
