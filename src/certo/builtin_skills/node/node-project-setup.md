---
name: node-project-setup
paths:
  - "package.json"
  - "**/package.json"
description: Path-triggered rule (not a keyword skill) — fires when the agent touches a package.json, to keep the project's scripts checkable.
---

This project has a `package.json`. Keep it checkable:

- A real `test` script that runs at least one test and exits with an
  error when a test fails (`node --test`, or the project's test
  framework). `npm init`'s placeholder (`echo "Error: no test
  specified" && exit 1`) is not a test.
- A `build` script when the project has a build step, and nothing that
  waits for input or keeps running (no watch mode, no dev server) in
  `test` or `build`.
- Install with `npm install <package>` (or `--save-dev` for tools only
  the tests and build use) so `package.json` and `package-lock.json`
  both record it; keep the lockfile. When a lockfile exists, `npm ci`
  installs exactly what it lists.
- Create projects with the non-interactive form of a scaffolder
  (`npm init -y`, `--yes`, `--no-interactive`, a `--template`); a prompt
  with no one to answer it creates nothing.
- Run `npm test` (and `npm run build` if there is one) before finishing.
