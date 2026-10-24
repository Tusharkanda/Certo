# One escalation run past failing tests: half-done work handed on (Certo 0.1.23)

One real `certo --escalate` run where the first model, a local one,
leaves the task half done and its fix attempt doesn't help. Certo hands
the folder to a cloud model, which keeps what works, fixes the rest and
passes the checks. It shows what the next model receives and what it
does with half-finished work. It is one run, not a benchmark.

The output below is copied from the run. The folder paths are shortened;
nothing else is changed.

## The setup

- **Certo:** 0.1.23 (not released yet), from a source checkout at commit
  `77dea16`. **Run:** 2026-10-24, from 16:47 UTC.
- **Machine running Certo:** Darwin 25.6.0, arm64, Apple M1, 16 GB RAM.
  `qwen3-coder:30b` ran on Ollama 0.40.6 on another machine.
- **Settings:** the defaults (checks on, up to 2 fix attempts, 30 minutes
  and 50 steps), plus a cost cap, `CERTO_MAX_TASK_COST=0.50`. The folder
  was not inside any git repository, and no `AGENTS.md` or `CLAUDE.md`
  was in it or above it.
- **The task:** `ledger-transfers` from Certo's benchmark tasks: fix two
  bugs in a small Python package and add a feature (find transfers
  between your own accounts, and leave them out of the monthly report).
- **The starting folder:** the task's starter files, plus the task's own
  tests already in `tests/` (`test_money.py`, `test_store.py`,
  `test_transfers.py`, from the task's reference solution). This is the
  "tests first" way of working: the tests say what done means before any
  model starts. They fail at the start, because `ledger/transfers.py`
  doesn't exist yet. The benchmark's hidden tests were not in the folder;
  they were run only at the end, to grade the result.
- **Command:**

  ```bash
  certo tasks/ledger-transfers.md --project ledger --escalate
  ```

The ladder, `default` in `escalation.yaml`:

```yaml
escalation:
  ladders:
    default:
      - model: qwen3-coder-local
        retries: 1
      - model: claude-haiku-5-5
```

## What it printed

The start:

```text
── Certo 0.1.23 ────────────────────────────────────────────
  Model    escalate: qwen3-coder-local → claude-haiku-5-5
  Folder   …/handoff-demo/projects/ledger (project ledger)
  Runs on  this computer
  Checks   on, up to 2 fix attempts
  Limits   30 min · 50 steps · $0.50
────────────────────────────────────────────────────────────
Note: …/handoff-demo/projects/ledger isn't a git repository, so the agent's changes there can't be rolled back with git.
Escalation: explicit ladder 'default', 2 rung(s):
  1. qwen3-coder-local (1 fix attempt(s); effort default)
  2. claude-haiku-5-5 (effort high)
```

After 11 minutes of local work, the handoff:

```text
Certo verification: the fix attempt just made produced no observable change — the same check (pytest failed (exit 1)) is still failing with identical output (ignoring timing). Stopping early rather than spending the rest of the retry budget on attempts that already provably didn't help — this project needs manual attention.
Certo: qwen3-coder-local ended no_progress after 1 fix attempt; escalating to claude-haiku-5-5 (rung 2 of 2).
```

The end of the run:

```text
Verification: verified

Run summary:
  Total running time: 13m 12s
  Models: ollama/qwen3-coder:30b (effort default), anthropic/claude-haiku-5-5 (effort high)
  Total tokens: 3,153,493 (input 3,118,762, of which cached 1,013,674; output 34,731)
  Total cost: $0.0298
    - ollama/qwen3-coder:30b (effort default): 2,047,534 tokens, $0.0000
    - anthropic/claude-haiku-5-5 (effort high): 1,105,959 tokens, $0.0298
  Rungs:
    1. qwen3-coder-local (ollama/qwen3-coder:30b, effort default): no_progress, 1 fix attempt, 11m 02s, 2,047,534 tokens, $0.0000
    2. claude-haiku-5-5 (anthropic/claude-haiku-5-5, effort high): verified, 0 fix attempts, 2m 09s, 1,105,959 tokens, $0.0298
  Final result from rung 2 (claude-haiku-5-5).
```

## What the second model received

A fresh conversation in the same folder, with the files as the first
model left them. Its first message, from the run's records (the folder
paths are shortened, and the task text, which follows "The task:", is
left out here):

```text
Another model already worked on this task in this folder and couldn't finish it. Its files are still here, exactly as it left them: look at them first, keep what works, and complete the task. This summary was written by Certo from what it recorded, not by a model.

- Model: qwen3-coder-local (ollama/qwen3-coder:30b, effort default)
- Result: no_progress
- Fix attempts after failed checks: 1
- Files it created: ledger/transfers.py
- Files it changed: ledger/money.py, ledger/reports.py, ledger/store.py
- Files it deleted: none
- Checks failing when it stopped: pytest (`…/projects/ledger/.venv/bin/python -m pytest -q`)

The task:

[…]

Output of the checks that were failing:

### pytest (`…/projects/ledger/.venv/bin/python -m pytest -q`) — pytest failed (exit 1)

.............................................F                           [100%]
=================================== FAILURES ===================================
_________ test_an_equal_transaction_outside_the_transfer_still_counts __________

    def test_an_equal_transaction_outside_the_transfer_still_counts():
        out = tx("Out", -500, day=OUT, category="x")
        twin = tx("Out", -500, day=OUT, category="x")
        inc = tx("In", 500, day=OUT, account="savings", category="x")
>       assert monthly_totals([out, twin, inc]) == {(2025, 11): {"x": Money(Decimal("-500"))}}
E       AssertionError: assert {} == {(2025, 11): ...rency='EUR')}}
[…]
FAILED tests/test_transfers.py::test_an_equal_transaction_outside_the_transfer_still_counts
1 failed, 45 passed in 0.06s
```

It did not get the first model's conversation.

## What it shows

- **The first model did most of the work, then got stuck.** `qwen3-coder`
  fixed both bugs, wrote `find_transfers` and changed the report: 45 of
  the 46 tests passed. One case was wrong: it compared transactions by
  value, so an identical transaction that wasn't part of a transfer
  disappeared from the report. Its one fix attempt left exactly the same
  failure, so Certo stopped it with `no_progress` instead of spending the
  second attempt.
- **Its own summary was wrong.** It ended with "All tests now pass,
  including the new transfer functionality tests." One test was failing.
  Certo went by the test run, not by that sentence.
- **The second model continued; it didn't restart.** `claude-haiku-5-5`
  read the files first, kept the first model's fixes for both bugs (it
  checked them, and said so), and replaced only the part that was wrong:
  transfers are now matched by position, and the report leaves them out
  by identity, not by value. It also added the tests the task asked for
  that were still missing (a Beta Bank import with `(1,234.50)`, and a
  transaction stored without a category getting one from a rule added
  later), plus tests for what it fixed (identical transactions, and a
  report given a one-time iterable). It only added to the existing test
  files; no existing test was changed or removed.
- **The hidden tests agree.** Run on the final folder, the task's 27
  hidden tests passed, 27 of 27.
- **The local part was slow and free, the cloud part fast and cheap.**
  11 minutes on the local model for $0, then 2 minutes and $0.03 on
  Haiku.
- **The run left its records.** `MODEL_DECISIONS.md` in the project
  records the ladder, the climb with its reason (`no_progress after 1 fix
  attempt`), and why the climb stopped.

## Limits

One task, one run. The tests were in the folder before the run started.
That is how this run was set up, and it matters: two earlier tries
without them didn't climb at all.

- On the Wordle sample, `qwen3-coder` finished alone in 1m 39s
  (`verified`, its own single test passing), so no other model was
  called.
- On this same task without the tests, `qwen3-coder` ended `verified`
  in 5m 41s, but the hidden tests failed 9 of 27. It fixed the first bug
  in the wrong place, never changed the report, and wrote no tests for
  the two fixes. The tests it did write passed. Certo can only check
  what the project's tests check, so a model that writes weak tests can
  still pass. See [Why agents lie](../concepts/why-agents-lie.md); tests
  written independently of the model are planned.

A third try, with this setup but with the project inside Certo's own
repository, also climbed (`retry_exhausted` → `verified`). It is not the
run shown here: the agent SDK also reads `CLAUDE.md` from the enclosing
git repository, for Claude models only, so the second model there saw
Certo's own development notes and the first didn't.
