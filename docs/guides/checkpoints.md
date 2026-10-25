# Go back to an earlier point

This guide shows how to put a project's files back as they were at an
earlier point of a Certo run: before the agent started, or after one of
its fix attempts. It is for anyone running `certo` on a folder, with or
without git.

## What Certo keeps

During a run, Certo takes a **checkpoint** (a snapshot of the project's
files):

- before the agent starts (`before the agent`, or `before the resumed
  run` with `--resume`);
- each time it runs the project's checks: after the agent's first try,
  and after each fix attempt (with `--escalate`, for every model on the
  ladder);
- when the run ends, if the files changed since the last one.

A checkpoint the files haven't changed since is skipped. Checkpoints
stay between runs, so a project collects them; they are numbered from 1.

With `--escalate` and `CERTO_ESCALATION_HANDOFF=restart`, Certo also uses
them itself: before each model after the first, it keeps the previous
model's work as a checkpoint (`before rollback`) and puts the files back
as they were `before the agent` (`rolled back to N`). See
[Start each rung from the original files](escalate-between-models.md#start-each-rung-from-the-original-files).

They live in the project's `.certo/checkpoints/` folder, a separate git
repository that Certo keeps for itself. Your own git repository, if
there is one, is never touched: no commit, branch, stash or change to
what you staged. A folder that isn't a git repository gets checkpoints
too. Git must be installed; without it there are none, and the run goes
on as before.

## List them

From the project folder:

```bash
certo checkpoints
```

From a real run (`claude-haiku-5-5`, adding a function and its tests to
a one-file project; the folder path is shortened):

```text
Checkpoints of /tmp/calc (in .certo/checkpoints/):
  1  2026-10-25 17:08  before the agent
  2  2026-10-25 17:09  checks 1: verified

Put the files back as they were at one of them: certo rollback N
```

`checks 1: verified` is the first time the checks ran and what they
said. A run with fix attempts has `checks 1: failed`, `checks 2: …` and
so on, and with `--escalate` each line starts with the model, as in
`rung 2 (claude-sonnet), checks 1: verified`. At the end of a run,
Certo prints how many there are and the two commands.

## Go back to one

```bash
certo rollback 1
```

Certo shows what it would change and asks before it does. From the same
run:

```text
Rolling back /tmp/calc to checkpoint 1 (before the agent):
  deleted: README.md
  restored: calc.py
  deleted: pytest.ini
  deleted: tests/test_calc.py
Done: the files are as they were at checkpoint 1.
Your files before the rollback are checkpoint 2: `certo rollback 2` undoes it.
```

- `restored`: the file goes back to how it was.
- `deleted`: the file didn't exist then, so it is removed.
- `added back`: the file existed then and was deleted since.

Before it changes anything, Certo takes a checkpoint of your files as
they are, so a rollback can always be undone with another one, as the
last line says. In a script, or anywhere nobody can answer the question,
add `--yes`.

For a project in another folder, give its path:
`certo checkpoints projects/calc`, `certo rollback 1 projects/calc`.

## What isn't in a checkpoint

- Files your `.gitignore` ignores.
- Environments, caches and build output: `.venv/`, `venv/`,
  `node_modules/`, `__pycache__/`, `dist/`, `build/`, `target/` and the
  like. The tools rebuild them.
- Certo's own `.certo/` folder.
- Files over 10 MB.

A rollback never touches these. Empty folders also stay: in the run
above, `tests/` is still there after the rollback, without its file.

## Turn them off

Set `CERTO_CHECKPOINTS=no`. They are also off when the run keeps no
state (`CERTO_SAVE_STATE=no`), and in server mode and `certo bench`,
which don't keep state in the project either.

Certo never rolls back on its own: a fix attempt that makes things worse
stays, and the next attempt or model continues from it. Checkpoints are
for you to go back when you decide to.

## Related

- [Resume an interrupted run](resume-a-run.md): continue instead of
  going back.
- [Work on an existing project](work-on-an-existing-project.md): commit
  first, so your own git history is the undo too.
- [Commands](../reference/commands.md#certo-checkpoints).
