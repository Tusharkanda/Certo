# Benchmark the cheap-cloud-first ladder: claude-haiku-5-5, then claude-sonnet-5-5

**Context.** The README shows a ladder that starts on a cheap cloud model and moves to a stronger one only when the first can't finish, and says plainly that it "hasn't been benchmarked yet". Certo's escalation has been measured only with a local model first ([Escalation in 0.1.17](https://github.com/alessioricco/certo/blob/main/docs/benchmark/escalation-0.1.17.md)). I'd welcome a `certo bench` run that compares the ladder with each model alone, so the README can show a number instead.

**This one needs API credits.** It calls Anthropic's API, so you need your own key and you pay for the runs. The plan below, printed by `certo bench` before anything starts, estimates **at most about $81** for 81 runs. That estimate is known to be high: it prices every run at about 500,000 input tokens, and real runs use far less (in the 0.1.17 escalation run, `claude-haiku-5-5` averaged about $0.01 per run). `repeats: 1` cuts it to a third, and `--max-cost` stops starting new runs once the real cost reaches a limit.

```text
Benchmark plan
  Tasks: 9 (task set 1)   Arms: 3   Repeats: 3   Runs: 81
  haiku: single, claude-haiku-5-5 (anthropic/claude-haiku-5-5, ~$0.30 per run), 27 run(s)
  sonnet: single, claude-sonnet-5-5 (anthropic/claude-sonnet-5-5, ~$1.20 per run), 27 run(s)
  haiku-then-sonnet: escalate, claude-haiku-5-5 (...); claude-sonnet-5-5 (...), 27 run(s) (at most ~$1.50 per run if every rung runs; ...)
  Estimated cost: at most ~$81.00 (rough: assumes ~500k input and ~20k output tokens per run)
```

**What done looks like.** A new issue opened with the **Benchmark results** form, with `results.md` and the `bench.yaml` below. The interesting numbers: how often the ladder stayed on Haiku, its cost per solved task against Sonnet alone, and any fooled runs (Certo said `verified`, the hidden tests failed).

**Where to start.**
- [Benchmark models and strategies](https://github.com/alessioricco/certo/blob/main/docs/guides/benchmark.md) and [Write a benchmark file](https://github.com/alessioricco/certo/blob/main/docs/guides/write-a-benchmark-file.md). Both models must be enabled in your `models.yaml`; `certo init models` can set them up.
- The `bench.yaml`, in the format of [`docs/benchmark/bench-0.1.17-escalation.yaml`](https://github.com/alessioricco/certo/blob/main/docs/benchmark/bench-0.1.17-escalation.yaml):

```yaml
tasks: all
repeats: 3
arms:
  - {name: haiku,  strategy: single, model: claude-haiku-5-5}
  - {name: sonnet, strategy: single, model: claude-sonnet-5-5}
  - {name: haiku-then-sonnet, strategy: escalate, models: [claude-haiku-5-5, claude-sonnet-5-5]}
```

One difference to mention in your results: the README's `cheap-first` ladder gives Haiku one fix attempt (`retries: 1`). A bench arm can't set that per model ([bench.yaml reference](https://github.com/alessioricco/certo/blob/main/docs/reference/bench-yaml.md#strategy-escalate)), so every rung uses the default number of fix attempts.

**How to check it.**
```bash
certo bench --config bench.yaml --max-cost 20   # prints the plan and asks before starting
```

**Labels:** help wanted, benchmark
