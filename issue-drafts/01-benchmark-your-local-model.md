# Run Certo's benchmark on a local model it hasn't measured

**Context.** Certo's advice on local models comes from its own benchmark, and so far that covers only six models on one kind of setup ([Choose a local model](https://github.com/alessioricco/certo/blob/main/docs/guides/choose-a-local-model.md#what-certos-benchmark-found)). `qwen2.5-coder:7b`, the suggestion for smaller machines, has never been measured. If you have a GPU or an Apple silicon Mac, I'd welcome a run of `certo bench` with a local model that isn't in that table, or with one that is but on different hardware.

**What done looks like.** A new issue opened with the **Benchmark results** form (it asks for your Certo version, hardware and model server, your `bench.yaml`, and the whole `results.md`). Fooled runs, where Certo said `verified` but the hidden tests failed, are the most useful thing to point out.

**Where to start.**
- [Benchmark models and strategies](https://github.com/alessioricco/certo/blob/main/docs/guides/benchmark.md): how `certo bench` works and how to read the results.
- [Write a benchmark file](https://github.com/alessioricco/certo/blob/main/docs/guides/write-a-benchmark-file.md): how to add your model to the model files and write `bench.yaml`.
- [Ollama and local models](https://github.com/alessioricco/certo/blob/main/docs/guides/ollama-and-local-models.md): give Ollama a large context window first.
- A file to start from: [`docs/benchmark/bench-0.1.18-local.yaml`](https://github.com/alessioricco/certo/blob/main/docs/benchmark/bench-0.1.18-local.yaml). Replace its two arms with one arm for your model.

**Cost.** A local model costs nothing, but it takes time: the 0.1.18 run of two models, 27 runs each, took about 7 hours. With `repeats: 1` instead of 3, one model takes roughly an hour. Runs go one at a time.

**How to check it.**
```bash
certo check                                  # the model makes real tool calls
certo bench --config bench.yaml              # prints the plan, then asks before starting
```
The results are in `bench-results/<date>/results.md`. Share only `results.md` and your `bench.yaml`: the rest of the folder holds every run's code and conversation.

**Labels:** good first issue, benchmark, help wanted
