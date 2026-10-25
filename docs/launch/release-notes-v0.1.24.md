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
