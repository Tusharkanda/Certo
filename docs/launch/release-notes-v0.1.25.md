# Certo v0.1.25

Not released yet.

## New: independent tests can change the verdict

`--independent-tests-strict` (or `CERTO_INDEPENDENT_TESTS_STRICT=yes`)
turns [independent tests](../guides/independent-tests.md) on and lets
them decide: when the project's checks pass but most sets of independent
tests fail, the verdict is `independent_failed` instead of `verified`,
and Certo exits with 1.

```text
Verification: independent_failed
Independent tests: failed, 2 of 3 sets failed (written from the task by m).
```

Only a `failed` result changes the verdict; `split`, `none` and
`couldn't run` leave `verified` as it is, and other verdicts stay as
they are. `--independent-tests` alone is still report only. The choice
comes from the 0.1.24 measurements: the tests caught 7 of 8 runs that
had fooled Certo on saved projects, and failed 1 of 38 right runs in
live ones, with a wrong test. So strict is for scripts and pipelines
where a false `verified` costs more than a second look. See
[Make them change the verdict](../guides/independent-tests.md#make-them-change-the-verdict)
and [`independent_failed`](../guides/after-the-verdict.md#independent_failed).

## New: checkpoints, and `certo rollback`

During a run Certo now takes a snapshot of the project's files before
the agent starts, each time it runs the checks (after the first try and
after every fix attempt, for every model with `--escalate`) and at the
end. `certo checkpoints` lists them, and `certo rollback N` puts the
files back as they were at one, after showing what it would change and
asking:

```text
Rolling back /tmp/calc to checkpoint 1 (before the agent):
  deleted: README.md
  restored: calc.py
  deleted: pytest.ini
  deleted: tests/test_calc.py
Done: the files are as they were at checkpoint 1.
Your files before the rollback are checkpoint 2: `certo rollback 2` undoes it.
```

They live in `.certo/checkpoints/`, a git repository Certo keeps for
itself: it works in any folder, and your own git repository is never
touched. Ignored files, environments and files over 10 MB are left out.
Certo never rolls back on its own. `CERTO_CHECKPOINTS=no` turns them
off. See [Go back to an earlier point](../guides/checkpoints.md).

## Fixed: the run record holds the final verdict

With `CERTO_ARTIFACTS_DIR` set and one model, a run whose acceptance
checks failed was recorded as `verified` in its `metadata.json`, though
Certo printed `acceptance_failed`: the record was written before the
acceptance checks ran. Now it is written after them (and after
`--independent-tests-strict`).

## Fixed: a model call can't outlast the time budget

0.1.24 stopped a run at `CERTO_MAX_TASK_SECONDS`, but a call to the
model already under way still finished, and could be retried: up to
`CERTO_LLM_TIMEOUT_SECONDS` six times (a benchmark run with a local
model spent about 50 minutes on four calls). Now, on local runs, a call
can't wait longer than the time left, and isn't retried once the budget
is gone, so a task ends within seconds of its budget. The work so far is
still checked once, as before. See
[`budget_exhausted`](../troubleshooting.md#budget_exhausted).

## New: Certo knows a local model's context window

The agent framework under Certo learned a model's context window from
LiteLLM, which knows nothing about Ollama models, and Ollama cuts a
prompt that is too long without an error: the model silently lost the
start of the task. Now Certo asks the Ollama server which window the
model got, and refuses one under 16,384 tokens with the fix. And
`CERTO_LLM_CONTEXT_TOKENS=32768` (or `context_tokens` in `models.yaml`)
asks Ollama for that size with every request, without restarting it.
See [Give the model a large enough context window](../guides/ollama-and-local-models.md#give-the-model-a-large-enough-context-window).

Knowing the window also lets a long run go on when it fills up: the agent
framework now summarizes the older steps, keeping the task and the
latest steps (`CERTO_CONDENSE`, on by default). It only acts near the
window, so a run that fits is unchanged; the run summary says
`Older steps summarized` when it happened. In
[a benchmark](../benchmark/context-0.1.25.md) with `qwen3.8:27b` at
32K, on the larger tasks, 3 of 8 runs passed the hidden tests with
condensing and 0 of 8 without. The sample is small, and most runs ran
out of time before the window filled.

In `certo bench`, an arm can set `context_tokens` (a smaller window for
a local model, without restarting Ollama) and `condense: false`, and each
run's record counts its condensations. See
[the benchmark file](../reference/bench-yaml.md#arms).

A benchmark's results now also record, for each Ollama model, the
server's address, its Ollama version and the context window it gives the
model, so a local result can be traced to how the model was served
([#5](https://github.com/alessioricco/certo/issues/5)). See
[Read the results](../guides/benchmark.md#read-the-results).

## New: a cost limit for every run

`CERTO_MAX_TASK_COST` used to limit only escalation, between rungs. Now
it limits every task: Certo reads the cost every few seconds and stops
the agent once the task has cost that much, fix attempts and independent
tests included. The checks still run once, so passing work is
`verified`; anything else ends with the new verdict `cost_exhausted`
(exit 1), which doesn't climb under escalation. The banner shows the
limit. See [Limit what a task can spend](../guides/run-records-and-costs.md#limit-what-a-task-can-spend).

## New: benchmark `--auto-model`

`certo bench` has a third strategy, `auto`: each task starts on the model
its task profile ranks first, with fallbacks, as `certo --auto-model`
does. `models: [...]` limits the candidates, and a new `task_profiles_file`
key names the profiles. The plan says which model each task will start
on, each record keeps the task's profile, and `results.md` counts how
many runs started on each model. See
[`strategy: auto`](../reference/bench-yaml.md#strategy-auto).

## New: escalation can restart each model from the original files

With `CERTO_ESCALATION_HANDOFF=restart`, the next model on a ladder starts
from the files as they were before the first model, not from the
previous model's half-done work. That work is kept as a checkpoint
first, so `certo rollback` can bring it back, and the next model still
gets Certo's note on what was tried and the failing checks. It is off by
default until a benchmark shows when it helps; a benchmark escalate arm
takes `handoff: restart` to compare. See
[Start each rung from the original files](../guides/escalate-between-models.md#start-each-rung-from-the-original-files).

## Fixed: a Node project with no tests is no longer `verified`

`node --test` exits successfully when it finds no test files, so a
project whose `npm test` ran nothing was `verified`. Now Certo reads how
many tests ran from the summary (`node --test`, and Jest's or Vitest's
"no tests found"): none makes the verdict `inconclusive`, as it already
was for Python, Go and Rust
([#23](https://github.com/alessioricco/certo/issues/23)). See
[Verification by language](../reference/verification-by-language.md#node-in-detail).

