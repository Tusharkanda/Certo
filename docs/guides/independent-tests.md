# Independent tests

This guide shows how to have Certo write tests for a task **before** the
agent builds it, and run them on the result. They check the agent's work
against the task, not against the agent's own tests.

> **New and report only.** The result is printed next to the verdict, but
> it doesn't change the verdict or the exit code. An independent test can
> itself be wrong, and how often is still being measured.

## Why

Certo's verdict comes from the project's own tests. When the agent writes
those tests, they can share its misunderstanding: a rule the task states
that neither the code nor the tests get right. Then the checks pass and
the verdict is `verified`, although the work is wrong. Independent tests
are written by someone who never saw the agent's work.

## Turn them on

```bash
certo tasks/ledger.md --project ledger --independent-tests
```

Or set `CERTO_INDEPENDENT_TESTS=yes` for every run. They work with one
model, `--auto-model` and `--escalate`, on local runs.

## What happens

1. **Before the build**, a separate, short conversation with the same
   model (with `--escalate`, the first model on the ladder) reads the task
   and a copy of the project as it is before the agent starts. It writes
   tests for what the task states, or none when the task doesn't say what
   to call (a function, a command, an endpoint) or in which language.
2. **The tests stay outside the project** while the agent works, so the
   agent can't see, run or change them.
3. **After the verdict**, Certo copies the tests into the project, runs
   them, and removes them again.

They can be written in Python (pytest), Node (`node --test`), Go and Rust.
For a Go or Rust project the task must name the module or crate.

## What you see

From a real run (`ledger-transfers`, one of Certo's benchmark tasks, with
`claude-haiku-5-5`):

```text
Certo: writing independent tests from the task with anthropic/claude-haiku-5-5.
Certo: independent tests written (test_bugfixes.py, test_transfers.py); the agent won't see them.
[…]
Verification: verified
Independent tests: failed, 1 failed, 17 passed in 0.03s (written from the task by anthropic/claude-haiku-5-5; report only).
  - .certo_hidden_tests/test_transfers.py::test_amount_sign_and_currency_must_match
```

In this run the agent's work was right (the task's hidden tests passed 27
of 27), and the failing independent test was wrong: it read a rule of the
task the wrong way. That is why the result is a report, not a verdict.
When an independent test fails, read it before you trust it either way.

Other results:

- `Independent tests: passed, …`: they all passed.
- `Independent tests: none (…)`: no tests were written; the reason
  follows, often that the task names nothing to call.
- `Independent tests: couldn't run (…)`: the tests couldn't run, for
  example a missing toolchain.

## Keep the tests

With [`CERTO_ARTIFACTS_DIR`](../reference/configuration.md) set, the
tests are kept in the run's record folder, under `independent_tests/`, so
you can read the one that failed. They are never left in the project,
where a later task's agent could see them.

## Costs and limits

- **Cost:** one extra short conversation per task. Its tokens and cost
  are part of the run summary. In the run above, the whole task cost
  $0.043.
- **Not on `--resume`**: the project already holds earlier work, so it
  isn't "before the build" any more.
- **Not with `--execution docker`**, and not in server mode yet.
- **Vague tasks get none.** The writer only tests what the task or the
  existing code names; it doesn't guess. See
  [Write a good task](write-a-good-task.md).

## Related

- [How verification works](../concepts/how-verification-works.md)
- [Acceptance checks](acceptance-checks.md): your own pass or fail rules.
- [Configuration](../reference/configuration.md): `CERTO_INDEPENDENT_TESTS`.
