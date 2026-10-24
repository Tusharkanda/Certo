# Certo v0.1.24

Not released yet.

## New: independent tests (report only)

`--independent-tests` (or `CERTO_INDEPENDENT_TESTS=yes`) has tests written
**before** the agent builds: a separate, short conversation with the same
model reads the task and the project as it is then, and writes tests for
what the task states. The agent never sees them. After the verdict, Certo
runs them and prints the result under it, naming any failing test:

```text
Verification: verified
Independent tests: failed, 1 failed, 17 passed in 0.03s (written from the task by anthropic/claude-haiku-5-5; report only).
  - .certo_hidden_tests/test_transfers.py::test_amount_sign_and_currency_must_match
```

Report only: the verdict and the exit code don't change, because an
independent test can be wrong too (in the run above it was). Local runs,
not on `--resume`, not in server mode yet. See
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
