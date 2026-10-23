# Certo v0.1.23

Not released yet.

## New: the benchmark grades Go, Rust and Node tasks with packages

A benchmark task's hidden tests can now be Go (`_test.go`, run with
`go test`) or Rust (`.rs` integration tests, run with `cargo test`), and
a Node task may use packages: grading installs what `package.json`
declares (`npm ci` with a lock file, else `npm install`) before the
hidden tests run. Only the hidden tests decide the score, in every
language, and hidden tests that run nothing are an error, not a pass.
This is the groundwork for app-scale tasks; the bundled 9 tasks don't
change. How to write one:
[Contribute a benchmark task](../guides/contribute-a-benchmark-task.md).

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
