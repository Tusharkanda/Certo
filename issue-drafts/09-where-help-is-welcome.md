# Where help is welcome

Certo is a small project with one maintainer, and contributions are welcome: code, docs, benchmark tasks, and benchmark runs on hardware and models I don't have. Start with [CONTRIBUTING.md](https://github.com/alessioricco/certo/blob/main/CONTRIBUTING.md): how to set up, run the tests (no API key needed) and what a pull request should include.

Each issue below says why it matters, where to start, and how to check your work. Comment on one before you start, so two people don't pick the same thing.

## Small first steps

- #9 The --resume hint leaves out a projects folder set for one command (taken: pull request #14)
- #10 Price the benchmark plan from earlier runs' cost.json
- #13 Guide: run certo verify before every commit (taken: pull request #16)
- #4 Move the historical planning docs into docs/history/
- #5 Record the Ollama version and context length in benchmark results

## Bigger pieces

- #11 --model alone fails when no model is configured (taken: pull request #17)
- #12 --auto-model with no model files: error after the banner, and a run is recorded (taken: pull request #15)
- #23 A Node project with no test files counts as `verified`
- #19 Verification for Ruby projects
- #20 Verification for PHP projects
- #21 Verification for C#/.NET projects
- #22 Verification for Swift packages
- #7 Tests and Python verification assume the macOS/Linux virtual environment layout (Windows)

## Benchmarks

- #18 Run Certo's benchmark on a local model it hasn't measured
- #24 Benchmark the cheap-cloud-first ladder: claude-haiku-5-5, then claude-sonnet-5-5
- #3 Contribute a benchmark task that catches models out

Found a wrong verdict, where Certo said `verified` and the work was broken? That's the most valuable report of all: use the **Wrong verdict** issue form.
