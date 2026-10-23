# Certo v0.1.23

Not released yet.

## New: the benchmark grades Go, Rust and Node tasks with packages

A benchmark task's hidden tests can now be Go (`_test.go`, run with
`go test`) or Rust (`.rs` integration tests, run with `cargo test`), and
a Node task may use packages: grading installs what `package.json`
declares (`npm ci` with a lock file, else `npm install`, never running
install scripts) before the
hidden tests run. Only the hidden tests decide the score, in every
language, and hidden tests that run nothing are an error, not a pass.
This is the groundwork for app-scale tasks. How to write one:
[Contribute a benchmark task](../guides/contribute-a-benchmark-task.md).

## New: larger benchmark tasks (task set version 2)

- `ledger-transfers`: work inside an existing Python package of several
  modules, with its own tests. Two bugs show up far from their cause,
  and a new feature has exact rules (a 0-to-3-day window, one transfer
  per transaction, earliest first) that a model's own tests tend to
  skip.
- `library-loans`: the HTTP API of a lending library in Go, standard
  library only, with "today" passed in: ISBN-13 check digits, due dates
  and capped fines, loan limits, exact status codes and JSON errors, and
  no book lent twice under concurrent requests.
- `room-bookings`: an HTTP API and its page rendered with React, in
  Node: booking rules on quarter hours, overlaps, free time between
  bookings, and titles shown as text. The only task that installs
  packages (`react` and `react-dom` 19.0.0, from a lock file).
- `todo-deps`: a to-do command-line program in Rust, standard library
  only, where tasks wait for other tasks: a list kept in a file between
  runs, cycles refused, exact output and exit codes. Its hidden tests
  run only the built program.

The nine small tasks don't change. To compare with a baseline
made on version 1, list those nine under `tasks:`; see
[Benchmark models and strategies](../guides/benchmark.md#the-tasks).

## Fixed: a command-line program that needs arguments passes verification

Certo runs each Python program with no arguments to check that it
starts. A command-line program that needs a subcommand rightly stops
with its usage line and exit code 2, and Certo counted that as a
failure. It cost a fix attempt, and the agent was pushed to change
correct behaviour: on the new `ledger-transfers` task, Sonnet made the
program print its help and exit 0 with no subcommand, which nobody asked
for. Now exit 2 with a `usage:` line passes, as "started and asked for
arguments". A crash still fails.

## Removed: the old skill folders and `certo-admin skills`

As announced in 0.1.22, Certo no longer reads `./skills`
(`CERTO_SKILLS_DIR`) or `./third_party_skills/`
(`CERTO_THIRD_PARTY_SKILLS_DIR` and `CERTO_THIRD_PARTY_SKILLS_LOCK`),
and `certo-admin skills` is gone. Skills live in
`~/.config/certo/skills/` and `<project>/.certo/skills/`, managed with
`certo skills`.

If you still have skills in the old folders, add each one again with
`certo skills add PATH --global` (or `--project NAME`); see
[Moving from the old folders](../guides/manage-skills.md#moving-from-the-old-folders).
While one of the three settings is still set, Certo prints a warning
naming it.
