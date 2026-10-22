# Choose a local model

This guide helps you pick a model to run Certo on your own machine, from
Certo's own benchmark results and with a quick test of your own setup.
How to install Ollama, give a model enough memory and reach it on another
machine is in [Ollama and local models](ollama-and-local-models.md).

## What makes a local model work with Certo

Three things matter, in this order:

1. **It makes real tool calls.** The agent works by calling tools: run
   a command, edit a file. A model that writes the call as text instead
   ends the run before any work is done. This depends on the model *and*
   on how Ollama serves it, so a model that works for someone else can
   fail on your setup.
2. **It gets the details right.** Certo checks the work with the
   project's tests, but the agent writes those tests. A model that
   misreads a rule writes tests that miss it, and the result is
   `verified` but wrong (see
   [Write a task Certo can check](write-a-good-task.md#3-give-the-expected-answers-yourself)).
3. **It is fast enough.** A task has a 30-minute budget by default
   (`CERTO_MAX_TASK_SECONDS`). A model that is right but slow can end
   `budget_exhausted`: its work is still checked if its last step ends
   after the budget, but there is no time left for a fix attempt.

## What Certo's benchmark found

Certo's benchmarks run each model 27 times on 9 small tasks, graded by
hidden tests the agent never saw. Two runs so far:
[0.1.15](../benchmark/baseline-0.1.15.md) with four models and
[0.1.18](../benchmark/baseline-0.1.18-local.md) with two. Each run used
one Ollama server, but not the same setup, so compare times only within
a run.

| Model | Correct | Fooled | Median time per task | Run | In short |
|---|---|---|---|---|---|
| `qwen3.8:27b` | 27/27 | 0 | 7m 37s | 0.1.18 | The best result so far: the default in `certo init`. |
| `qwen3.8:27b` | 24/27 | 0 | 4m 37s | 0.1.15 | Its 3 failures were tool calls written as text. |
| `gemma4:31b-it-qat` | 26/27 | 1 | 12m 40s | 0.1.15 | Accurate, but slow. |
| `qwen3-coder:30b` | 18/27 | 3 | 8m 20s | 0.1.18 | Wrote wrong code more often; the default before 0.1.19. |
| `devstral-small-2:24b` | 5/27 | 1 | 51s | 0.1.15 | Mostly wrote its tool calls as text. |
| `qwen3.6:35b-a3b` | 0/27 | 0 | 19s | 0.1.15 | Wrote its tool calls as text in every run. |

"Fooled" counts the runs where Certo said `verified` but the hidden
tests failed.

How to read it:

- **Start with `qwen3.8:27b`** if your machine can hold it: it passed
  every task in the 0.1.18 run, and Certo was never fooled by it.
- **Try `gemma4:31b-it-qat`** when correctness matters more than time, and
  raise `CERTO_MAX_TASK_SECONDS` for bigger tasks.
- **Don't rule out `qwen3.6` or `devstral` from this table alone.** Their
  failures were tool calls written as text, which can come from the
  Ollama setup rather than the model. Check your own setup with the steps
  below.
- **Prefer `qwen3.8:27b` to `qwen3-coder:30b`.** In the same run,
  `qwen3-coder` passed 18 of 27, and 3 of its wrong answers were
  `verified`: its own tests missed rules the task stated.
- **`qwen2.5-coder:7b`**, the suggestion for smaller machines, hasn't
  been benchmarked. Expect it to be weaker.
- The tasks are small, single-file ones. On bigger work, differences
  between models are likely to grow.

## Test a model on your setup

### 1. Check that it makes real tool calls

Pull the model, point Certo at it, and run `certo check`:

```bash
ollama pull qwen3.8:27b
export CERTO_LLM_MODEL=ollama/qwen3.8:27b
export CERTO_LLM_BASE_URL=http://localhost:11434
certo check
```

`certo check` makes one real call, and fails when the answer doesn't come
back as a tool call. A model that fails here will fail every task.

### 2. Run one small task

```bash
certo "Write a Python function that converts Celsius to Fahrenheit, with pytest tests" --project try-model
```

Watch for a run that ends within a minute with `inconclusive` or
`unchanged`. If the agent's last message is a tool call written as text,
such as `{"command": "view", ...}`, the model has the problem from step
1 even though `certo check` passed: see
[The run ends at once, with a tool call as the agent's last message](../troubleshooting.md#the-run-ends-at-once-with-a-tool-call-as-the-agents-last-message).

### 3. Compare models

For a first look, run one of your own tasks on each model with the
script in [Compare models on one task](compare-models-on-a-task.md).

For an answer you can trust, run `certo bench` with one arm per model. It grades every run with hidden tests and shows how
often each model was right, how long it took, and how often Certo was
fooled. See [Write a benchmark file](write-a-benchmark-file.md) ("Which
of my local models is best?").

Running all 9 tasks takes hours on a local model. To get a first answer
sooner, list only a few tasks and use one repeat.

## When a local model isn't enough

- Split the task into smaller steps (see
  [one step per task](write-a-good-task.md#7-one-step-per-task)).
- Resume a failed run with a stronger model:
  `certo --resume --model MODEL` (see [After the verdict](after-the-verdict.md)).
- Let Certo do that by itself: start every task on the local model and
  move to a cloud model only when verification fails. See
  [Escalate between models](escalate-between-models.md). In the same
  benchmark, `claude-haiku-5-5` solved all 9 tasks for under a cent each.
  With `qwen3.8-27b-local` first and haiku second, a ladder solved all 9
  for about a quarter of haiku's cost, with qwen3.8 doing 7 of them (see
  [Escalation in 0.1.17](../benchmark/escalation-0.1.17.md)).

## Related

- [Ollama and local models](ollama-and-local-models.md): install, memory,
  context window
- [Baseline 0.1.18, local](../benchmark/baseline-0.1.18-local.md):
  `qwen3.8:27b` against `qwen3-coder:30b`
- [Baseline 0.1.15](../benchmark/baseline-0.1.15.md): four local and
  three cloud models
- [Benchmark models and strategies](benchmark.md)
