# Independent tests on saved benchmark projects (Certo 0.1.24)

How often do [independent tests](../guides/independent-tests.md) catch
wrong work, and how often do they fail right work? To find out without
building anything again, `claude-haiku-5-5` wrote independent tests for
each of the 13 bundled benchmark tasks, three times each. Every set of
tests then ran on the projects that earlier `certo bench` runs had left
behind. For those projects, the hidden tests had already said whether
the work was right.

## The setup

- **Certo:** 0.1.24 (not released yet), from a source checkout.
  **Run:** 2026-10-24, from 21:20 UTC, with
  `scripts/replay_independent_tests.py`.
- **Writer:** `anthropic/claude-haiku-5-5`, at the effort set in the
  model list. It wrote each set the way `--independent-tests` does
  before a build: from the task text and the task's starter files.
  Three sets per task, 39 in all, for **$0.32**.
- **Projects:** 379 projects saved by 13 earlier benchmark runs (Certo
  0.1.13 to 0.1.23, local and cloud models), kept only when the run
  started after the task last changed. The hidden tests passed on 307
  and failed on 72. On 8 of the 72, Certo had said `verified`: it was
  fooled. Each task's reference solution and untouched starter were
  added too.
- Each project was copied before the tests ran, so the saved results
  weren't changed. Running the tests cost nothing.

## Results

One set of tests at a time (counted per project and test set):

| Projects | Should | As expected |
|---|---|---|
| Fooled Certo (`verified`, hidden tests failed) | fail | 22 of 24 |
| All wrong projects | fail | 210 of 216 |
| Untouched starters | fail | 39 of 39 |
| Right projects | pass | 723 of 921 |
| Reference solutions | pass | 34 of 39 |

- **They catch almost all wrong work,** including 7 of the 8 runs that
  fooled Certo, with every set of tests written.
- **One set alone raises many false alarms:** 198 of 921 on right
  projects. Most came from 5 of the 39 sets, each with one test that
  reads the task wrong. Such a test fails on nearly every project,
  reference solution included (the 5 reference failures).
- **The other failures on "right" projects were real bugs** the hidden
  tests don't check. Every one came from tests that agree with the
  task's text:
  - **`wordle-score`, 9 projects:** they accept `ÄBCDE`, though the task
    allows only `a` to `z`;
  - **`token-bucket`, 9 projects:** they accept `NaN` or `'1'` as
    `refillPerSecond`, though the task asks for a number greater than 0;
  - **`semver-order`, 5 projects:** they reject `1.0.0+01`, though the
    task forbids leading zeros only in numeric prerelease parts.

  All three sets of tests found each of these, on the same projects.

## Voting over three sets

A wrong test showed up in one set of three; a real bug, in all three.
So: count a project as failing only when at least two of its three sets
fail.

| Rule | Fooled caught | Wrong caught | Right projects flagged | Reference flagged |
|---|---|---|---|---|
| any 1 of 3 | 8 of 8 | 72 of 72 | 150 of 307 | 5 of 13 |
| 2 of 3 | 7 of 8 | 69 of 72 | 24 of 307 | 0 of 13 |
| 3 of 3 | 7 of 8 | 69 of 72 | 24 of 307 | 0 of 13 |

With two of three, the false alarms from wrong tests are gone: no
reference solution flagged, and the 24 right projects flagged are the
real bugs above (and one `todo-deps` project two sets agree on). It
still catches 7 of the 8 runs that fooled Certo. The one it misses is a
`duration-parser` run that only one set caught. The cost is three
writers instead of one: about $0.01 to $0.07 per task with this model.

## A local writer: qwen3.8

The same replay, with `ollama/qwen3.8:27b` (run locally through Ollama)
writing the tests, on the same 379 projects. **Run:** 2026-10-24 22:39
to 2026-10-25 03:11 UTC. Writing the 39 sets took about 4 hours 20
minutes, one at a time, and cost nothing.

- **2 of the 39 writes produced no tests,** both for `ledger-transfers`,
  the largest task.
- **One set of `todo-deps` tests was broken:** all 15 of its tests
  failed on every project, the reference solution included.

One set of tests at a time, next to Haiku's:

| Projects | Should | qwen3.8 | Haiku |
|---|---|---|---|
| Fooled Certo | fail | 11 of 24 | 22 of 24 |
| All wrong projects | fail | 189 of 210 | 210 of 216 |
| Untouched starters | fail | 37 of 37 | 39 of 39 |
| Right projects | pass | 835 of 913 | 723 of 921 |
| Reference solutions | pass | 32 of 37 | 34 of 39 |

With the 2-of-3 vote:

| Writer | Fooled caught | Wrong caught | Right projects flagged | Reference flagged |
|---|---|---|---|---|
| qwen3.8 | 2 of 8 | 61 of 72 | 5 of 307 | 1 of 13 |
| Haiku | 7 of 8 | 69 of 72 | 24 of 307 | 0 of 13 |

- **qwen3.8's tests are milder.** They raise fewer false alarms, but
  they miss more wrong work: with the vote, they catch only 2 of the 8
  runs that fooled Certo.
- **They found none of the real bugs** Haiku's tests found (`ÄBCDE`,
  `NaN`, `1.0.0+01`). Every failure on right work came from a wrong
  test: each one also failed the reference solution.
- **The 5 right projects flagged** are all `todo-deps`: the broken set
  plus a set with wrong tests.

So with this model, independent tests add little. They are more useful
written by a stronger model than the one doing the build.

## Limits

- **Old projects, small tasks.** All 8 fooled runs are on small tasks
  (`slugify`, `semver-order`, `duration-parser`, `inventory-fix`), from
  Certo 0.1.13 to 0.1.22. The four larger tasks had no fooled runs to
  test, and `library-loans` and `room-bookings` had no wrong projects.
- **Two writer models.** One cloud model and one local one, one replay
  each.
- **The writer judged other models' work.** In a real run the same model
  writes the tests and builds, which this replay doesn't show.
- **Writers can share a misreading.** In a live run afterwards
  (`ledger-transfers`, the same writer, three sets), all three sets
  failed right work on the same rule of the task, so the vote didn't
  help; three more sets for that task failed its reference solution 2 of
  3 times. In this replay the same task's sets passed it every time. See
  [Independent tests](../guides/independent-tests.md#what-you-see).
- "Right" means the hidden tests passed. Some of those projects have
  real bugs, as above, so a few "false alarms" in the first table are
  correct catches.

## Reproduce it

With `certo bench` results in `bench-results/` and the writer model
enabled in your `models.yaml`:

```bash
uv run python scripts/replay_independent_tests.py --model claude-haiku-5-5 \
    --results bench-results --out bench-results/independent-replay-haiku
```

The report is `report.md` in the output folder. Your numbers will
differ: the writer varies, and so do your saved projects.

## Related

- [Independent tests](../guides/independent-tests.md)
- [Benchmark baseline 0.1.23](baseline-0.1.23.md)
