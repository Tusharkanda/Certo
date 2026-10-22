# Certo v0.1.22

Not released yet.

## New: `certo skills`, for official and third-party skills

`certo skills list` shows every skill a run gets: Certo's official ones
and yours, in separate sections, with how each one fires, its size in
tokens, and which skill replaces which. `--task "..."` says which skills
would go into a run of that task, and why.

`certo skills add FILE_OR_FOLDER --global` (every project) or
`--project NAME` (one project) adds a skill you wrote, after checking that
it loads; `certo skills remove` takes it away. A skill from git
(`certo skills add github:OWNER/REPO PATH --global`) keeps the old rules:
exact commit, license check, off until `certo skills enable`. One of the
two flags is always required, so a skill never lands in the wrong place.

Third-party skills now live in `~/.config/certo/skills/` and
`<project>/.certo/skills/`, never in a folder git tracks. Until now they
lived in `./skills` and `./third_party_skills/`, relative to the folder
`certo` ran from, where they could end up in a repository. Those folders
are still read until the next release, and a run prints a line asking you
to move them. A skill of yours may still replace an official one of the
same name, but a run now says so. `certo-admin skills` moves into
`certo skills` and goes away in the next release.

## Changed: a run that ends after its time budget is still checked

Certo checks the time budget (`CERTO_MAX_TASK_SECONDS`, 30 minutes by
default) only between the agent's runs, so a slow model's last run can end
after it. Until now Certo then reported `budget_exhausted` without looking
at the work. In the 0.1.15 local benchmark, three runs ended that way
although their work passed the hidden tests.

Now the project's checks run once, with no fix attempt, because they need
no model. Work that passes is `verified`, with a note that the budget ran
out. Work that fails stays `budget_exhausted`, and the check results are
shown. A run that ended in an error, or with checks turned off, is
reported as before.

## Changed: escalation moves on when nothing could be checked

With `--escalate`, a model that wrote code but nothing Certo could check
(no test ran) ended `inconclusive`, and the climb stopped there. In the
0.1.17 escalation run, a local model wrote the module, then wrote its test
file as plain text instead of a tool call, so the next model was never
asked.

Now `inconclusive` moves the task to the next model, with a note asking it
to keep what works, finish the task and add tests that check it. If that
model also ends `inconclusive`, the project most likely has nothing Certo
can check, and the climb stops there instead of paying for every model.

## Also

- **`/v1/chat/completions` reports real token usage.** `usage` was always
  zero; it now counts the whole task (every model call, all models).
  Streaming adds a usage chunk with `stream_options: {"include_usage":
  true}`, as OpenAI does.
- **The reasoning effort is shown next to the model.** The run summary,
  the escalation lines and rungs, `STATUS.md`, `.certo/RUNS.md`,
  `MODEL_DECISIONS.md`, the run artifacts, server results and the
  benchmark's cost table now say which effort a model ran at, for example
  `ollama/qwen3.8:27b (effort default)`. A run time or a result means
  little without it, and a ladder that lists one model twice, at `low`
  and then `high`, used to show two rungs with the same name.
- **`certo init` gives Ollama a longer call timeout.** It now writes
  `CERTO_LLM_TIMEOUT_SECONDS=1200` when you choose Ollama. With the
  default, 300 seconds, `qwen3.8:27b` on a local server had answers that
  took longer, were dropped and restarted from scratch: a sample task lost
  about 20 of its 42 minutes that way, and another gave up after 5
  timeouts in a row. Existing settings files aren't changed; add the line
  by hand (see the Ollama guide).
- **Faster start.** `certo --version` and `certo --help` take about 0.1s
  instead of 3s, and `certo verify` on a small project 0.3s instead of
  3.2s: they no longer load the OpenHands SDK, which only commands that
  run an agent need.
- **`--model` alone is enough.** `certo "task" --model X` works with no
  model configured, and `--model` with `--base-url` needs no key for a
  local model. Thanks to @dbdefault (#17).
- **`--auto-model` with missing model files stops cleanly**: only the
  error, with no banner, no resume hint and no run recorded. Thanks to
  @dbdefault (#15).
- **The resume hint keeps your projects folder**: when
  `CERTO_PROJECTS_DIR` isn't the default, the printed `certo --resume`
  command includes it. Thanks to @dbdefault (#14).
- **Clearer escalation output on a provider failure.** When a model
  fails at the provider, the line says why in plain words ("the provider
  rejected its API key") instead of the raw provider error, which stays in
  `MODEL_DECISIONS.md`. Each escalation line is printed once (it was
  printed twice), the SDK's warning about an unshown error event is gone,
  the next model is no longer told that a model which never started
  "couldn't finish", and its `Task:` line shows the task's title, not the
  start of Certo's note. A rung that stopped at a provider error before
  changing a file is no longer credited in the project's `README.md`,
  and `MODEL_DECISIONS.md` says an explicit ladder comes from
  `escalation.yaml` (it said `models_list.yaml`). Seen live in a recorded
  run, now at the top of the README:
  [Escalation past a provider failure](../benchmark/escalation-provider-failure-0.1.22.md).
- **Benchmark transcripts say when each message arrived.**
  `runs/transcripts/<run>.json` has a `seconds` list beside the messages,
  counted from the run's start, so a slow run shows where its time went.

