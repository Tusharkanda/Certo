# bench.yaml

The format of the benchmark file read by `certo bench`. It is for looking
things up; the guides are [Benchmark models and strategies](../guides/benchmark.md)
and [Write a benchmark file](../guides/write-a-benchmark-file.md).

The default file is `./bench.yaml`; `certo bench --config FILE` reads
another. It holds no keys: models are named from the model files. A commented
example ships as [bench.yaml.example](../../src/certo/examples/bench.yaml.example), inside the
package (`certo/examples/`).

## Layout

```yaml
models_file: ./models.yaml             # optional
models_list_file: ./models_list.yaml   # optional
escalation_file: ./escalation.yaml     # optional
tasks_dir: ./my-tasks        # optional
tasks: all                   # or a list of task names
repeats: 3
arms:
  - name: qwen-local
    strategy: single
    model: qwen3-coder-local
```

## Top-level keys

| Key | Default | Meaning |
|---|---|---|
| `arms` | **required** | A non-empty list of arms (below). |
| `tasks` | `all` | `all`, or a list of task names. `certo bench --list-tasks` shows the names. |
| `repeats` | `1` | Runs per task per arm, a whole number of at least 1. Results vary between runs, so more repeats give a fairer comparison. |
| `models_file` | looked up | Your personal `models.yaml`. Without it: `./models.yaml`, else `~/.config/certo/models.yaml`. `CERTO_MODELS_FILE` is not read. |
| `models_list_file` | looked up | The model catalog, `models_list.yaml`, the same way. `CERTO_MODELS_LIST_FILE` is not read. |
| `escalation_file` | looked up | `escalation.yaml`, the same way, for the `cost_axis` and `max_rungs` of a derived `escalate` arm. Optional: without one, the defaults apply. `CERTO_ESCALATION_FILE` is not read. |
| `tasks_dir` | the bundled task set | A folder of your own tasks, in the same shape. |

Any other key is an error. Relative paths are relative to the folder where
you run `certo bench`.

## Arms

Every arm has:

| Key | Meaning |
|---|---|
| `name` | A unique name, made of letters, digits, `.`, `_` and `-`. It appears in the results and in file names. |
| `strategy` | How the arm runs a task. See below. |

Every arm can also have:

| Key | Meaning |
|---|---|
| `independent_tests` | Optional, `true` or `false` (default). With `true`, each run writes [independent tests](../guides/independent-tests.md) before the build, as `--independent-tests` does, and records their result. Report only: the verdict and the score don't change. Their writing isn't in the plan's cost estimate. |

The other keys depend on the strategy. An unknown strategy, or a key the
strategy doesn't take, is an error that lists what is allowed.

### `strategy: single`

One model, the normal Certo run: exactly what `certo "<task>"` does.

| Key | Meaning |
|---|---|
| `model` | The `name` of an entry in the models file. An unknown name is an error that lists the names the file has. |

### `strategy: escalate`

Escalation, as `certo --escalate` does it: start on the first model, and
move to the next one only when Certo's verdict shows the model couldn't
finish, or its provider fails.

| Key | Meaning |
|---|---|
| `models` | Optional. A list of at least two model names, in the order to climb. Without it, the arm uses the ladder Certo builds from the active models' ratings: the same ladder for every task, printed in the plan. |

```yaml
arms:
  - name: local-then-cloud
    strategy: escalate
    models: [qwen-local, gpt-luna]
  - name: derived
    strategy: escalate
```

Grading is the same as for every arm: the hidden tests decide. Each run
records every rung that ran and which one gave the final verdict.
The named ladders in `escalation.yaml` are not used here: an arm's ladder
is its `models` list, or a derived one.

## How models are used

- The arm's model is taken from the model files: its id, ratings,
  `reasoning_effort` and `timeout_seconds` from the list, its `api_key`,
  `base_url` and overrides from `models.yaml`. An empty field stays empty;
  it is never filled from `.env` or the environment's `CERTO_LLM_*`
  settings.
- An arm can only name a model that `models.yaml` enables. A model that is
  only in the list, or has `activated: false`, is an error that says how
  to enable it. (Before version 0.1.9 `activated` was ignored here.)
- Problems in the model files are checked as for every command (see
  [Checks](models-yaml.md#checks)): errors stop the benchmark,
  warnings are printed with the plan.
- `task_profiles.yaml` is not used. The `escalation` settings
  (`cost_axis`, `max_rungs`) are used only by a derived `escalate` arm, to
  build its ladder.

## Strategies to come

Strategies are a small registry in Certo's code, so new ones can be added
without changing how the benchmark runs, for example `best_of` (several
attempts, the verifier picks). `single` and `escalate` exist today.
