# Benchmark baseline: Certo 0.1.22

Two `certo bench` runs on the 9 bundled tasks: `qwen3.8:27b`, the local
model `certo init` suggests, three times each, and the same three cloud
models as in 0.1.15, once each. Every model ran alone. It checks that
0.1.22 didn't make results worse, with a local and with cloud models. How
the benchmark works, and what each column means, is in
[Benchmark models and strategies](../guides/benchmark.md). The previous
baselines are [0.1.18, local](baseline-0.1.18-local.md) and
[0.1.15](baseline-0.1.15.md).

## The setup

- **Certo:** 0.1.22. **Task set:** version 1 (`11b1105b535e`, bundled),
  9 tasks: 6 Python, 3 Node.
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
  16 GB RAM.
- **Local model:** on Ollama 0.40.6, on another machine, with a context
  length of 131,072 tokens and Q4_K_M quantization (read from Ollama's
  `/api/version` and `/api/ps` right after the run): the same setup as
  0.1.18. Each model call could take up to 1200 seconds.
- **Cloud run:** 2026-10-22, 20:39 to 20:48 UTC. 1 repeat, so 9 runs per
  model, three runs at a time (`--parallel 3`). Each model ran at
  reasoning effort `high`, from the model list.
- **Local run:** 2026-10-22, 20:48 to 23:46 UTC. 3 repeats, so 27 runs.
- **Results folders:** `bench-results/0.1.22-cloud` and
  `bench-results/0.1.22-local`, on the machine that ran them.

| Arm | Model |
|---|---|
| `qwen3.8` | `ollama/qwen3.8:27b` |
| `haiku` | `anthropic/claude-haiku-5-5` |
| `luna` | `openai/gpt-6-luna` |
| `sonnet` | `anthropic/claude-sonnet-5-5` |

## Results

| Arm | Hidden tests passed | Verified | Fooled | Caught | Unconfirmed passes | Median time | Cost per solved task |
|---|---|---|---|---|---|---|---|
| `sonnet` | 9/9 | 9/9 | 0 | 0 | 0 | 34s | $0.12 |
| `haiku` | 9/9 | 9/9 | 0 | 0 | 0 | 51s | $0.0095 |
| `luna` | 9/9 | 9/9 | 0 | 0 | 0 | 54s | $0.0057 |
| `qwen3.8` | 26/27 | 25/27 | 1 | 2 | 2 | 5m 44s | $0.00 |

Total cost: **$1.20**, all of it the cloud run (sonnet $1.07, haiku
$0.09, luna $0.05). The plan had estimated at most ~$14.54. No run
stopped with an error, and no cloud run needed a fix attempt.

Hidden tests passed, per task (local out of 3, cloud out of 1):

| Task | `qwen3.8` | `haiku` | `luna` | `sonnet` |
|---|---|---|---|---|
| duration-parser | 3 | 1 | 1 | 1 |
| inventory-fix | 3 | 1 | 1 | 1 |
| page-ranges | 3 | 1 | 1 | 1 |
| pedestrian-crossing | 3 | 1 | 1 | 1 |
| semver-order | 3 | 1 | 1 | 1 |
| slugify | **2** | 1 | 1 | 1 |
| temperature-table | 3 | 1 | 1 | 1 |
| token-bucket | 3 | 1 | 1 | 1 |
| wordle-score | 3 | 1 | 1 | 1 |

## What the results say

- **No sign that 0.1.22 made results worse.** The cloud models passed 9
  of 9, as in 0.1.15, at almost the same cost. `qwen3.8` passed 26 of 27
  (27 of 27 in 0.1.18). One run is within chance.
- **Certo was fooled once in 54 runs.** Of its 52 `verified` verdicts, 51
  were right. The one wrong verdict is the same `slugify` bug seen twice
  in 0.1.15 (see below).
- **Two correct local runs ended without `verified`.** In both, the code
  passed the hidden tests, but a test the agent wrote itself was wrong,
  so the project's own checks failed and Certo reported that
  (`no_progress` and `retry_exhausted`). Certo can't tell a wrong test
  from wrong code.
- **Tool calls written as text were rare.** One `qwen3.8` run wrote a
  tool call as plain text, twice; it is the `no_progress` run above. No
  other run did.
- **Every local run finished inside the 30-minute budget.** The longest
  took 29m 42s (`semver-order`, repeat 1). No run ended
  `budget_exhausted`.

## Compared with earlier baselines

| Arm | Earlier | 0.1.22 |
|---|---|---|
| `sonnet` | 9/9, 31s, $1.08 (0.1.15) | 9/9, 34s, $1.07 |
| `haiku` | 9/9, 45s, $0.08 (0.1.15) | 9/9, 51s, $0.09 |
| `luna` | 8/9, 1 fooled, 56s, $0.05 (0.1.15) | 9/9, 0 fooled, 54s, $0.05 |
| `qwen3.8` | 27/27, 0 fooled, 7m 37s (0.1.18) | 26/27, 1 fooled, 5m 44s |

The local run used the same Ollama setup as 0.1.18 (version, context
length, quantization and call timeout), so the times compare: the median
run was about two minutes shorter, with a little fewer input tokens (4.0
million against 4.3 million). Whether the 0.1.15 cloud run also ran
three at a time wasn't recorded, so read the cloud times loosely.

## The fooled run

- **`qwen3.8` · `slugify` · repeat 2.** The task says: shorten a long
  slug to the longest start that ends at a word boundary and is at most
  `maxLength` long. The code cut at the last hyphen *inside* the limit,
  so when the limit fell exactly at the end of a word, it dropped that
  word: `slugify('the quick brown fox', 9)` gave `"the"`, not
  `"the-quick"`. The agent's tests tried a limit at a word's end only for
  the first word (`3` gives `"the"`), where the bug doesn't show.
  `gemma4-qat` and `luna` wrote the same bug in 0.1.15.

The code passed every test the agent wrote, so `verified` was the honest
result of the checks Certo had. This is the gap described in
[Write a task Certo can check](../guides/write-a-good-task.md#3-give-the-expected-answers-yourself):
the agent's tests share its misunderstanding.

## The unconfirmed passes

- **`page-ranges` · repeat 2** (`no_progress`). The agent's test said
  `"-"` means every page; the task says it is invalid, and the code
  rightly raised `ValueError`. In its fix attempt the agent saw that its
  test was wrong, but its edit didn't apply, and twice it then wrote a
  tool call as text, which ended its turn. Its fix attempt changed
  nothing, so Certo stopped.
- **`wordle-score` · repeat 3** (`retry_exhausted`). The agent's test
  expected `score_guess("eeeee", "eaeza")` to mark one `e` correct; the
  answer has an `e` in the middle too, so the code rightly marked two.
  Two fix attempts left the test as it was.

## Reproduce this run

The two benchmark files are
[bench-0.1.22-local.yaml](bench-0.1.22-local.yaml) and
[bench-0.1.22-cloud.yaml](bench-0.1.22-cloud.yaml). Copy them, enable
their models in your `models.yaml`, and run:

```bash
certo bench --config bench-0.1.22-cloud.yaml --parallel 3
certo bench --config bench-0.1.22-local.yaml
```

Expect about 10 minutes for the cloud run and 3 hours for the local one
with the model on a separate machine. Your numbers will differ: models
vary between runs, and local times depend on the machine serving the
model.

## Limits of this baseline

- Nine small tasks. Every model solved almost all of them, so the tasks
  can't tell these models apart; they show only that nothing broke.
- One repeat for the cloud models: 9 runs each.
- One local model and one Ollama setup.
- Single-model arms only: escalation wasn't measured here. It is in
  [Escalation in 0.1.17](escalation-0.1.17.md).
- No skills of the user's own were installed. A benchmark run doesn't
  yet keep out skills in `~/.config/certo/skills/`.

## Related

- [Baseline 0.1.18, local](baseline-0.1.18-local.md)
- [Baseline 0.1.15](baseline-0.1.15.md)
- [Choose a local model](../guides/choose-a-local-model.md)
- [Benchmark models and strategies](../guides/benchmark.md)
- [Ollama and local models](../guides/ollama-and-local-models.md)
