# Run a task in milestones

This guide shows how to split a bigger task into milestones. Certo runs
them one at a time, each in its own conversation, and checks each one
before the next starts. When one fails, Certo stops there, keeps the
work done so far, and `certo --resume` continues from that milestone.

Milestone mode is [experimental](../README.md#experimental-features):
it works with one model, but hasn't been benchmarked yet.

## Write the task file

Start each milestone with a `## Milestone N: title` heading, numbered
1, 2, 3 in order. The text before the first heading is the context that
every milestone gets: what the project is, its language, its rules.

````markdown
# Temperature converter

A small Python module, `convert.py`, with pytest tests in `tests/`.
Standard library only, plus pytest for the tests.

## Milestone 1: Celsius and Fahrenheit
Add `c_to_f(c)` and `f_to_c(f)` to `convert.py`, each returning a float,
with tests.
```acceptance
[{"kind": "file_contains", "path": "convert.py", "contains": "def c_to_f"}]
```

## Milestone 2: Kelvin
Add `c_to_k(c)` and `k_to_c(k)`. A temperature below absolute zero
(below 0 K) raises `ValueError`. With tests.
````

A milestone may hold one ` ```acceptance ` block: a list of file checks,
in the same format as [acceptance checks](acceptance-checks.md). Certo
takes the block out of the text the agent gets.

Keep each milestone small enough to be one ordinary task: something you
could check by its tests when it is done. See also
[Write a task Certo can check](write-a-good-task.md).

## Run it

```bash
certo --milestones task.md --project temps
```

`--milestones` needs the task in a file; text or a URL is refused. Keep
the file outside the project folder, so the agent doesn't read the
acceptance checks.

For each milestone, Certo:

1. takes a [checkpoint](checkpoints.md) named `before milestone N`;
2. starts a new conversation with the context, the titles of the
   milestones already done, and this milestone's text;
3. runs it like any task, with the usual fix attempts, then checks the
   project's tests and the acceptance checks of this milestone and of
   every milestone before it (an earlier milestone that stops passing
   is a failure);
4. starts the next milestone only when the verdict is `verified`.

The time, cost and step limits (`CERTO_MAX_TASK_SECONDS`,
`CERTO_MAX_TASK_COST`, `CERTO_MAX_ITERATIONS`) apply to each milestone
separately: a task of 3 milestones can take up to 3 times the time.
`--acceptance-checks`, if you give it, applies to the last milestone.

## Read the result

Each milestone starts with a `Milestone N of M` line and ends with its
verdict. At the end, Certo lists every milestone. From a real run where
the second milestone failed its acceptance check (shortened):

```text
Milestone 2 of 2: acceptance_failed

Milestones:
  1. Celsius and Fahrenheit: verified
  2. Kelvin: acceptance_failed

Verification: acceptance_failed
  - Required acceptance check failed (file_exists CHANGELOG.md): CHANGELOG.md does not exist

Run summary:
  Total running time: 1m 49s
  Models: anthropic/claude-haiku-5-5 (effort default)
  Total tokens: 481,982 (input 467,323, of which cached 430,828; output 14,659)
  Total cost: $0.0162
```

The task is `verified` only when every milestone is. Otherwise its
verdict and exit code are those of the milestone where it stopped; see
[Verdicts](../reference/verdicts.md). The run summary adds up all the
milestones that ran. `.certo/RUNS.md` has one entry per milestone.

## Continue after a failure

```bash
certo --resume --project temps "Also add a CHANGELOG.md listing what each milestone added."
```

`--resume` skips the milestones already `verified` and continues the
first one that isn't, in its saved conversation when there is one. The
optional text is an extra instruction for that milestone. Then the
remaining milestones run as usual.

Certo reads the task file again, from where it was when the milestones
started. If the file was moved, deleted or edited since, `--resume`
refuses: a plan in progress doesn't change. To use an edited file, run
`certo --milestones` again; the milestones start from the first.

When every milestone is already `verified`, `--resume` says so and does
nothing.

## What Certo keeps

`.certo/milestones.json` holds the task file's path, a fingerprint of
its text, each milestone's title and its verdict. It never holds the
milestones' text or their acceptance checks: the agent can read
`.certo/`. `.certo/STATUS.md` lists the milestones with their verdicts;
see [Resume an interrupted run](resume-a-run.md#the-certo-folder).

A new task in the same folder without `--milestones` forgets the
milestones.

## Not yet

- `--escalate` and `--independent-tests` can't be combined with
  `--milestones` yet.
- Certo doesn't plan milestones for you: they come from the task file.

## Related

- [Commands](../reference/commands.md#certo): `--milestones`, `--resume`
- [Acceptance checks](acceptance-checks.md)
- [Go back to an earlier point](checkpoints.md)
