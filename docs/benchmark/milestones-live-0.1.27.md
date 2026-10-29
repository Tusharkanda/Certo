# Milestone mode: the first live runs, Certo 0.1.27

Five live runs on `claude-haiku-5-5`, made while milestone mode was
built (2026-10-29). They are not a benchmark: one small task, one run
each. They show that each part works end to end, with real numbers.
A benchmark of milestone mode on a bigger task comes next.

## The task

A temperature converter in two milestones: Celsius and Fahrenheit, then
Kelvin with a check for temperatures below absolute zero. Each milestone
has an acceptance block.

- [milestones-temperature.task.md](milestones-temperature.task.md): the
  task as written.
- [milestones-temperature-changelog.task.md](milestones-temperature-changelog.task.md):
  the same task, but milestone 2 also needs a `CHANGELOG.md` that its
  text never asks for, so that milestone fails on purpose.
- [milestones-escalation.yaml](milestones-escalation.yaml): the
  `claude-haiku-5-5` → `claude-sonnet-5-5` ladder of the last two runs.

**Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 8 CPUs,
16 GB RAM. Every run had a $0.10 cost limit per milestone ($0.30 with
the ladder).

## The runs

| # | What it tested | Command | Result | Time | Cost |
|---|---|---|---|---|---|
| 1 | Two milestones, one model | `certo --milestones --model anthropic/claude-haiku-5-5 --project temps milestones-temperature.task.md` | both `verified` | 1m 07s | $0.0133 |
| 2 | A milestone that fails | same, with `milestones-temperature-changelog.task.md` | milestone 1 `verified`, milestone 2 `acceptance_failed` (no `CHANGELOG.md`), exit 1 | 1m 49s | $0.0162 |
| 3 | Continue it | `certo --resume --model anthropic/claude-haiku-5-5 --project temps "Also add a CHANGELOG.md listing what each milestone added."` | milestone 2 continued in its saved conversation, `verified` | 13.6s | $0.0110 |
| 4 | A ladder and independent tests per milestone | `certo --milestones --independent-tests --escalate cloud --project temps milestones-temperature-changelog.task.md` (ladder without `escalate_on_acceptance_failed`) | milestone 1 `verified`; milestone 2 `acceptance_failed` on rung 1, no climb (as that ladder says); independent tests passed 3 of 3 sets on both | 1m 55s | $0.0367 |
| 5 | Start a failed milestone again on the ladder | `certo --resume --independent-tests --escalate cloud --project temps` (ladder as in the file above) | milestone 2 started again on rung 1 in a fresh conversation, told how the last try ended; Haiku added `CHANGELOG.md`; `verified`, independent tests 3 of 3 | 47.2s | $0.0186 |

Runs 4 and 5 used `CERTO_ESCALATION_FILE=docs/benchmark/milestones-escalation.yaml`.

## What the runs showed

- **Each milestone ran in its own conversation** and was checked before
  the next started. The `Milestones:` list, `.certo/STATUS.md` and
  `.certo/RUNS.md` (one entry per milestone) matched the verdicts.
- **The agent reads `.certo/`.** In an earlier run, the agent
  read the first version of `.certo/milestones.json`, which held every
  milestone's acceptance checks, and reasoned from them. Since then the
  file keeps only the task file's path, a fingerprint, titles and
  verdicts; run 1 was made after that change.
- **Not seen live yet:** a climb to the next rung inside a milestone
  (rung 1 solved every milestone), and a resume after Ctrl-C (the
  interrupt sent during a test didn't reach the run). Tests without a
  model cover both.

## Reproduce it

Enable `claude-haiku-5-5` and `claude-sonnet-5-5` in your `models.yaml`,
copy the task files outside your project folder, then run the commands
above. All five runs together cost about $0.10.
