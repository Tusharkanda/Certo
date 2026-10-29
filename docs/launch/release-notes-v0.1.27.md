# Certo v0.1.27

Not released yet.

## New (experimental): run a task in milestones

`certo --milestones task.md` splits a task file at its
`## Milestone N: title` headings and runs the milestones one at a time,
each in its own conversation. Each one must be `verified` before the
next starts: its own work, the project's tests, and the acceptance
checks of every milestone so far, written in an ` ```acceptance ` block
inside the milestone. When one fails, Certo stops there and keeps the
earlier work; `certo --resume` continues that milestone, then the rest.

```text
Milestones:
  1. Celsius and Fahrenheit: verified
  2. Kelvin: verified

Verification: verified
```

The time, cost and step limits apply to each milestone. Certo keeps only
the milestones' titles and verdicts in `.certo/`, never their acceptance
checks, because the agent can read that folder.

With `--escalate`, each milestone climbs its own ladder from the first
rung, and `certo --resume --escalate` starts a failed milestone again on
the first rung, told how the last try ended. With `--independent-tests`,
each milestone gets its own tests, written before it starts. See
[Run a task in milestones](../guides/run-in-milestones.md).

## Benchmark: tasks in milestones

A benchmark arm with `milestones: true` runs a task written in
milestones milestone by milestone; any other arm gets the same task in
one go, so one task compares the two ways. Each run's record lists the
milestones' verdicts. For a task whose hidden tests are named by
milestone (`test_m1_...`), `results.md` shows the hidden tests passed
per milestone. See
[the benchmark file reference](../reference/bench-yaml.md#arms) and
[Benchmark models and strategies](../guides/benchmark.md).
