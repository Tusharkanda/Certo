# Certo v0.1.22

Not released yet.

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
  and the next model is no longer told that a model which never started
  "couldn't finish".
- **Benchmark transcripts say when each message arrived.**
  `runs/transcripts/<run>.json` has a `seconds` list beside the messages,
  counted from the run's start, so a slow run shows where its time went.

