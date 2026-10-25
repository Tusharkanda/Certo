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
`Older steps summarized` when it happened.

