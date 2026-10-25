# Certo v0.1.24

Not released yet.

## New: independent tests (report only)

`--independent-tests` (or `CERTO_INDEPENDENT_TESTS=yes`) has tests written
**before** the agent builds: three separate, short conversations with the
same model each read the task and the project as it is then, and write a
set of tests for what the task states. The agent never sees them. After
the verdict, Certo runs every set and prints the result under it. The
result is `failed` only when most sets fail (2 of 3), because a wrong
test usually turns up in one set only; `CERTO_INDEPENDENT_TESTS_SETS`
changes how many sets are written.

```text
Verification: verified
Independent tests: failed, 3 of 3 sets failed (written from the task by anthropic/claude-haiku-5-5; report only).
  - set 1: failed (1 failed, 22 passed in 0.04s): .certo_hidden_tests/test_transfers.py::test_outgoing_must_be_negative_and_incoming_positive[100.00--100.00]
  - set 2: failed (1 failed, 25 passed in 0.03s): .certo_hidden_tests/test_transfers.py::test_amounts_must_be_equal_and_opposite[100--100]
  - set 3: failed (1 failed, 14 passed in 0.03s): .certo_hidden_tests/test_transfers.py::test_amounts_must_match_in_size_currency_and_sign
```

Report only: the verdict and the exit code don't change, because
independent tests can be wrong too. In the run above all three were,
misreading the same rule of the task. Measured on 379 saved benchmark
projects, three sets with a 2-of-3 vote caught 7 of the 8 runs that had
fooled Certo, and failed none of the reference solutions, with
`claude-haiku-5-5` writing them. Written by the local `qwen3.8:27b`,
they caught only 2 of the 8:
[Independent tests on saved projects](../benchmark/independent-tests-replay-0.1.24.md).
Local runs, not on `--resume`, not in server mode yet. See
[Independent tests](../guides/independent-tests.md).

## New: independent tests in `certo bench`

A benchmark arm can turn them on with `independent_tests: true`. Each
run writes them before the build and records their result, and
`results.md` counts how often they failed on right work and on runs
that fooled Certo. See
[the benchmark file](../reference/bench-yaml.md#arms).

## Changed: Certo doesn't start while OpenHands plugins would load

OpenHands, the agent toolkit under Certo, loads plugins into every run on
its own: from your user folders (`~/.agents/plugins/`,
`~/.openhands/plugins/`) and, for a project Certo generates, from a git
repository around it. A plugin can add skills, tools and hooks that
Certo hasn't checked. Now Certo looks before a run, and before
`certo bench`, and doesn't start when it finds one, naming each plugin
and its folder. A project's own plugins, and a repository's plugins when
you run Certo on an existing folder, are still fine. See
[OpenHands plugins](../guides/manage-skills.md#openhands-plugins).

## New: a verified run lists the check files the agent changed

`verified` means the project's checks passed, but an agent can make
them pass by weakening them. Now Certo keeps a copy of the test files
and check settings before the run, and after a `verified` run lists
each one the agent changed or deleted:

```
Verification: verified
  - The agent changed 1 file the checks rely on: tests/test_calc.py (1 line changed). The checks passed on the changed files; read the changes before you trust them.
```

The verdict stays `verified`, since the task may have asked for the
change (this one did). See
[Changed check files](../reference/verdicts.md#changed-check-files).

## New: `certo bench --stop-at`, for a benchmark over several nights

`--stop-at 07:00` stops starting new runs at that local time (tomorrow
if it's already past today). The run in progress finishes and is saved,
so a long benchmark can run one slice per night and continue with
`--resume`, without stopping it by hand and losing a run. See
[Benchmark models and strategies](../guides/benchmark.md#run-it).

## Fixed: the time budget now stops a run in progress

`CERTO_MAX_TASK_SECONDS` was checked only between runs, so one terminal
command could wait for hours: a run in the 0.1.23 baseline waited 10,000
seconds. Now the agent is stopped after its current step when the
budget runs out, and a terminal command can't ask to wait longer than
the time left; the agent is told to use a shorter timeout. A model call
already under way still finishes. See
[`budget_exhausted`](../troubleshooting.md#budget_exhausted).
