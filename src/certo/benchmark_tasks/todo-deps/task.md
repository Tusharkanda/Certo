# A to-do list with dependencies, in Rust

Write `todo`, a command-line to-do list in Rust where a task can wait for
other tasks. `Cargo.toml` is already here: keep the package name `todo`,
use only the standard library (no crates), and keep `cargo test` passing.
Add tests of your own.

## Where the list is kept

In the file named by the environment variable `TODO_FILE`, or `todo.txt`
in the current folder when it isn't set. A missing file is an empty
list. Choose the file's format yourself; titles must survive it exactly
as given (any characters except a line break, including tabs, `|`, `#`,
quotes and non-ASCII text).

## Commands

Each task has an id: 1 for the first task ever added, then 2, 3, and so
on. An id is never reused, even after its task is removed.

- `todo add TITLE... [--after ID]...` adds a task. The title is the
  words given, joined with single spaces; `--after ID` (any number of
  times, anywhere after `add`) makes it wait for task ID. Prints
  `added N`, its id.
- `todo done ID` marks a task done and prints `done ID`.
- `todo block ID --after OTHER` makes task ID also wait for task OTHER,
  and prints `ID waits for OTHER`. Adding a wait that is already there
  changes nothing and still succeeds.
- `todo remove ID [--force]` removes a task and prints `removed ID`.
  Without `--force`, a task that another task waits for can't be
  removed. With `--force`, it is removed and dropped from every other
  task's waits.
- `todo list` prints every task, by id, one per line:
  `[ ] 3 Cook dinner` for an open task, `[x] 1 Buy food` for a done one.
  An open task that still waits for open tasks ends with their ids, in
  ascending order: `[ ] 3 Cook dinner (after 1, 2)`. Waits for done
  tasks aren't shown. An empty list prints nothing.
- `todo next` prints the open task with the lowest id whose waits are
  all done, in the same form as `list` (`[ ] 2 Buy food`), or
  `nothing to do` when there is none.

## Errors

Nothing is printed to standard output and the file is left unchanged.

- **Exit code 1**, with one line on standard error that starts with
  `error: `:
  - a task that doesn't exist (`error: no task 7`), in any command,
    including `--after 7`;
  - `done` on a task that is already done (`error: task 2 is already
    done`);
  - `done` on a task that waits for open tasks:
    `error: task 3 is blocked by 1, 2`, listing the open ones in
    ascending order;
  - `block` that would make a task wait for itself, directly or through
    other tasks: `error: task 1 would wait for itself`;
  - `remove` without `--force` on a task another task waits for:
    `error: task 1 is needed by 3, 4`, listing those tasks in ascending
    order.
- **Exit code 2**, with a line on standard error that starts with
  `usage:`: no command, an unknown command, a missing title or id, an id
  that isn't a positive whole number, or an unknown option.
