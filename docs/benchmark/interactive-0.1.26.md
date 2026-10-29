# Benchmark: the testable-interactive-apps skill, Certo 0.1.26

Three `certo bench` runs. They answer one question: when a task
describes a terminal game, does Certo's `testable-interactive-apps`
skill get the agent to write tests, so Certo can say `verified`, and
does it leave a cloud model no worse?

Each run has two arms on the same model: one with the skill, one
without it (`skills_off: [testable-interactive-apps]`).

## The setup

- **Certo:** 0.1.26 (unreleased, with the skill of the
  `phase-1.8-skills` branch).
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Task `hangman-cli`** (task set `skills-1`, `c6747d83871c`, in
  `skill-tasks/`): a Hangman game for the terminal, played from
  standard input. The task never asks for tests. 12 hidden tests.
- **Local run:** `ollama/qwen3.8:27b` (build `aaee06c39dcf`), on
  Ollama 0.40.6 on another machine, with a 32,768-token window
  (`context_tokens: 32768`). 3 repeats per arm, one run at a time, on
  2026-10-29 from 08:49 to 09:49 UTC.
  **File:** [bench-0.1.26-interactive-local.yaml](bench-0.1.26-interactive-local.yaml).
- **Cloud run:** `anthropic/claude-haiku-5-5` on `hangman-cli`, 3
  repeats per arm, on 2026-10-27 from 19:06 to 19:16 UTC.
  **File:** [bench-0.1.26-interactive-cloud.yaml](bench-0.1.26-interactive-cloud.yaml).
- **Bundled task set:** `wordle-score` is the only task of task set
  version 2 (`6ed42dae4bca`) where the skill fires (on "game").
  `claude-haiku-5-5`, 3 repeats per arm, on 2026-10-27.
  **File:** [bench-0.1.26-interactive-wordle.yaml](bench-0.1.26-interactive-wordle.yaml).
- **Results folders:** `bench-results/interactive-0.1.26-local-r2`,
  `bench-results/interactive-cloud-0.1.26` and
  `bench-results/interactive-wordle-0.1.26`, on the machine that ran
  them. A first local run on 2026-10-27 got no answer from the Ollama
  server, so all its runs were network errors; it is not counted.

## Results

| Task | Arm | Hidden tests passed | Verified | Fooled | Runs that wrote tests | Median time | Tokens out | Cost |
|---|---|---|---|---|---|---|---|---|
| hangman-cli | `qwen-no-skill` | 2/3 | 0/3 | 0 | 0/3 | 4m 45s | 22,835 | $0.00 |
| hangman-cli | `qwen-skill` | 2/3 | 3/3 | 1 | 3/3 | 17m 56s | 70,661 | $0.00 |
| hangman-cli | `haiku-no-skill` | 2/3 | 3/3 | 1 | 3/3 | 1m 25s | 42,699 | $0.042 |
| hangman-cli | `haiku-skill` | 3/3 | 3/3 | 0 | 3/3 | 2m 06s | 49,603 | $0.053 |
| wordle-score | `haiku-no-skill` | 3/3 | 3/3 | 0 | 3/3 | 56s | 31,218 | $0.033 |
| wordle-score | `haiku-skill` | 3/3 | 3/3 | 0 | 3/3 | 1m 02s | 30,016 | $0.034 |

Per local run (verdict, hidden tests, time):

| Repeat | `qwen-no-skill` | `qwen-skill` |
|---|---|---|
| 1 | `inconclusive`, 11/12, 4m 45s | `verified`, passed, 7m 31s |
| 2 | `inconclusive`, passed, 6m 02s | `verified`, passed, 18m 21s |
| 3 | `inconclusive`, passed, 4m 42s | `verified`, 11/12 (fooled), 17m 56s |

## What the results say

- **With the skill, qwen3.8 wrote tests every time.** Without it, it
  wrote none in 3 of 3 runs, so Certo had nothing to run and every run
  ended `inconclusive`, even the two that worked. This matches a
  baseline run on 2026-10-27: hidden tests passed 3/3, `verified` 0/3,
  no tests. With the skill, all 3 runs were `verified`.
- **One `verified` qwen run was wrong.** Both failing qwen runs, one in
  each arm, had the same bug: a wrong letter guessed a second time cost
  a second miss (the task says a repeated letter costs nothing). The
  run with the skill had a test for a repeated letter, but only for a
  right one, so its tests passed and Certo said `verified`. Without the
  skill, the same bug ended `inconclusive`. The skill makes Certo's
  answer more often `verified`; that answer is only as good as the
  tests the agent writes.
- **The skill made qwen3.8 three times slower.** Median 18 minutes
  instead of 5, and three times the output tokens, mostly writing and
  fixing its tests. All runs stayed well inside the 30-minute budget.
- **The cloud model was not worse.** `claude-haiku-5-5` already wrote
  tests without the skill, so the skill changed little: hangman 3/3
  hidden instead of 2/3, wordle the same 3/3. On hangman it cost 27%
  more ($0.053 instead of $0.042 for 3 runs); on wordle 2% more.
- **Haiku's fooled run without the skill** printed a `Guess: ` prompt
  without a new line, so its next board line began `Guess: Word: ...`
  instead of `Word: ...`. The hidden test reads only lines that begin
  with `Word:`. The task asks for the board as its own line, but
  doesn't mention a prompt, so this one is as much the hidden test's
  strictness as the program's bug. Since task set `skills-2`, the task says each board line
  stands alone, with no prompt before it.
- **Small sample:** 3 runs per arm. A difference of one run between
  arms can be chance.

## What this means

- **The skill does what it was built for on a local model:** a working
  game is now `verified` instead of `inconclusive`. It stays on.
- **It moves the risk to the agent's tests.** 1 of 3 `verified` qwen
  runs was wrong. Turning on independent tests
  (`--independent-tests`) is the way to check the agent's own tests
  when that matters.
- **On a cloud model it costs a little and changes little.**

## Reproduce it

Enable `qwen3.8-27b-local` (`ollama/qwen3.8:27b`) and `claude-haiku-5-5`
in your `models.yaml`, then, from the repository root:

```bash
certo bench --config docs/benchmark/bench-0.1.26-interactive-local.yaml
certo bench --config docs/benchmark/bench-0.1.26-interactive-cloud.yaml
certo bench --config docs/benchmark/bench-0.1.26-interactive-wordle.yaml
```

The local file takes about an hour on a setup like this one. The two
cloud files take about 10 minutes each and $0.10 together.
