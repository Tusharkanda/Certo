# Write a benchmark file

This guide shows how to set up your own `certo bench` file, step by step:
which models it can use, which arms to put in it for the question you want
answered, and how to check the plan before anything runs. What the
benchmark measures, and how to read its results, is in
[Benchmark models and strategies](benchmark.md). Every key is in the
[bench.yaml reference](../reference/bench-yaml.md).

## 1. Make the models available

A benchmark file names models; it never holds keys or addresses. Those
come from the model files, the same ones `--auto-model` and `--escalate`
use:

- **`models_list.yaml`**, the catalog: every model's id and ratings.
- **`models.yaml`**, your settings: the models you use, with their key or
  server address.
- **`escalation.yaml`**, optional: `cost_axis` and `max_rungs` for the
  ladder an `escalate` arm derives. An arm's own `models:` list is its
  ladder; the named ladders in this file aren't used.

If you don't have them yet, copy the examples that ship with Certo: when
a model file is missing, Certo's error message prints the `cp` command.
See
[The model files](../reference/models-yaml.md).

A benchmark can only use a model that `models.yaml` lists and doesn't
mark `activated: false`. Before writing the benchmark file, check that
each one answers:

```bash
certo check --models
```

Every model you plan to benchmark needs a passing line. A model that fails
here fails every benchmark run too.

## 2. Start from the example

Certo ships a commented example inside the package. Run `certo bench` in
the folder where you want the file: when there is no `bench.yaml`, it
prints the command that copies the example there, with the right path for
your installation:

```text
Configuration error: benchmark file not found: bench.yaml. Certo ships an example to start from; copy it and name the models to compare:
  cp /path/to/certo/examples/bench.yaml.example bench.yaml
```

Run the `cp` line it printed. The example names `qwen3.8-27b-local` and
`gpt-6-luna`, the two models the example `models.yaml` enables. Change
them to models you enabled.

## 3. One question per file

An arm is one way of running a task: a model, used with a strategy. Put in
a file only the arms that answer one question, so the results compare
like with like. Some common questions:

**Which of my local models is best?** One `single` arm per model:

```yaml
# bench-local.yaml
tasks: all
repeats: 3
arms:
  - {name: qwen3.8,  strategy: single, model: qwen3.8-27b-local}
  - {name: gemma4,   strategy: single, model: gemma4-31b-local}
```

**Is my local model good enough, compared with a cloud one?** One local
and one cloud arm:

```yaml
# bench-local-vs-cloud.yaml
tasks: all
repeats: 3
arms:
  - {name: local, strategy: single, model: qwen3.8-27b-local}
  - {name: cloud, strategy: single, model: gpt-6-luna}
```

**Does escalation pay off?** The two models alone, and the two in a
ladder. A derived arm (no `models:`) adds the ladder Certo builds from
the ratings:

```yaml
# bench-ladder.yaml
tasks: all
repeats: 1
arms:
  - {name: local,  strategy: single, model: qwen3.8-27b-local}
  - {name: cloud,  strategy: single, model: gpt-6-luna}
  - {name: ladder, strategy: escalate, models: [qwen3.8-27b-local, gpt-6-luna]}
  - {name: derived, strategy: escalate}
```

Escalation only climbs when a model fails Certo's checks. On tasks the
first model already solves, an escalate arm gives the same result as that
model alone.

**Does `--auto-model` pick well?** An `auto` arm next to each of its
models alone. The plan shows which model each task starts on:

```yaml
# bench-auto.yaml
tasks: all
repeats: 1
arms:
  - {name: local,  strategy: single, model: qwen3.8-27b-local}
  - {name: cloud,  strategy: single, model: gpt-6-luna}
  - {name: picked, strategy: auto, models: [qwen3.8-27b-local, gpt-6-luna]}
```

**Does my setup work at all?** A quick run before a long one: a few tasks,
one repeat.

```yaml
# bench-smoke.yaml
tasks: [temperature-table, slugify]
repeats: 1
arms:
  - {name: local, strategy: single, model: qwen3.8-27b-local}
```

`certo bench --list-tasks` lists the task names.

## 4. Choose how many runs

The number of runs is tasks × arms × repeats. With 10 tasks and 3
repeats, each arm has 30 runs.

- **Repeats.** A model doesn't do the same thing twice, so one repeat
  shows roughly how a model does, and three make a comparison fairer.
  Even then, a difference of two or three runs between arms can be
  chance.
- **Time.** Runs with a local model go one at a time. In the
  [0.1.13 baseline](../benchmark/baseline-0.1.13.md) a local 27B model
  took a median of about 6 minutes per run, and a cloud model under a
  minute. With several local models, Ollama loads a different model for
  almost every run (runs go one repeat at a time across all arms), which
  adds to each run's time.
- **Cost.** Cloud runs cost money. Add a cap with `--max-cost` (step 6).

## 5. Check the file and the plan

Run the benchmark without `--yes`:

```bash
certo bench --config bench-local.yaml
```

Certo checks the file first. A mistake, such as an unknown model name, a
model that isn't enabled or an unknown key, stops it with a message that
says what to fix. Then it prints the plan: the arms, the models each one
uses, the number of runs and a rough cost estimate. Answer `n` to stop
there; nothing has run yet.

## 6. Run it

Give each benchmark file its own results folder, so you can tell results
apart and continue the right one later:

```bash
certo bench --config bench-local.yaml --out bench-results/local-1
certo bench --config bench-ladder.yaml --out bench-results/ladder-1 --max-cost 5
```

- Answer `y` to start, or add `--yes` to skip the question.
- If a run stops (Ctrl-C, a crash, a closed laptop), continue it with the
  same file and folder: `certo bench --config bench-local.yaml --resume
  --out bench-results/local-1`. Without `--out`, `--resume` takes the
  newest folder in `bench-results/`, which may belong to another file;
  Certo then refuses it, since the arms don't match.
- Two benchmarks at once are fine when at most one of them uses local
  models. Two that use the same Ollama server compete for it and slow
  each other down.

## 7. Keep the files, or not

A benchmark file holds no keys, so you can commit it, for example to
compare the same arms after a change. If your files name models other
people don't have, keep them out of git instead (add `bench*.yaml` to
`.gitignore`). The results folders (`bench-results/` by default) are
large and personal: they hold a copy of every run's code and its whole
conversation, so they usually stay out of git.

When you publish or share results, share the benchmark file with them:
it is the exact recipe, so others can run it and compare. Certo does this
for its own results: the files behind each baseline are in
`docs/benchmark/`, next to the results pages, for example
[bench-0.1.15-local.yaml](../benchmark/bench-0.1.15-local.yaml).

## Related

- [Benchmark models and strategies](benchmark.md): what the benchmark
  measures, the cost estimate, and how to read the results.
- [bench.yaml reference](../reference/bench-yaml.md): every key.
- [Commands: certo bench](../reference/commands.md#certo-bench): every
  flag.
- [Escalate between models](escalate-between-models.md): how ladders
  work.
