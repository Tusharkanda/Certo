# Manage skills

A skill is a short Markdown file of instructions, such as "how we write
pytest tests". A run gives the agent the skills that fit its task. This
guide shows which skills a run gets, and how to add your own, for every
project or for one.

## Official and third-party skills

There are two kinds, kept apart:

- **Official skills** come with Certo. A new release can change them;
  nothing else does.
- **Third-party skills** are yours: written by you, or downloaded from
  someone else. They live in one of two folders, outside any git
  repository's tracked files:

| Scope | Folder | Applies to |
|---|---|---|
| Global | `~/.config/certo/skills/` | every project on this computer |
| Project | `<project>/.certo/skills/` | one project (`.certo/` is never committed: it ignores itself) |

A project can also have **its own** skills, `.agents/skills/` and
`AGENTS.md`, which you may commit and share with other tools. Certo reads
them but never writes them (see [The project's own skills](#the-projects-own-skills)).

When two skills have the same name, the later one in this order wins:
official, global, project, the project's own. So a skill of yours can
replace an official one, for example to change `pytest-conventions`. A run
then prints a line saying so, and `certo skills list` shows it.

## See what a run gets

```bash
certo skills list
certo skills list --project hanoi
```

Each skill shows how it fires and roughly how many tokens it adds. Size
matters on a local model with a small context. To see what one task would
get, and why:

```bash
certo skills list --project demo --task "Build a snake game with pytest tests"
```

```text
For the task 'Build a snake game with pytest tests':
  From its first message (about 334 tokens):
    repository-discovery (official): "build" is in the task
    my-style (global): "game" is in the task
    pytest-conventions (project): "pytest" is in the task
  Later, maybe:
    pin-dependencies (official): if the agent touches pyproject.toml, requirements*.txt
```

The matching is the same one a run uses: whole words, any case. "tests"
does not match the trigger "test".

## Add a skill you wrote

Write the skill as a Markdown file with a short header:

```markdown
---
name: my-style
triggers:
  - game
  - snake
---

Keep functions short. Put the game logic apart from the input and output,
so it can be tested.
```

Then add it for every project, or for one:

```bash
certo skills add my-style.md --global
certo skills add my-style.md --project demo
```

```text
Added 'my-style' to ~/.config/certo/skills. It is on.
  Fires when the task says: game, snake; about 5 tokens.
```

Certo loads the file the way a run would before copying it, so a skill
with a broken header is refused. If the folder already has a skill with
that name, Certo asks before replacing it (`--yes` skips the question).

The header decides when the agent gets the skill:

| Header | The agent gets the skill when |
|---|---|
| `triggers: [...]` | one of the words appears in the task or the conversation (whole word, any case) |
| `paths: [...]` | it works on a file that matches one of the patterns |
| neither | always |

A skill can also be a folder with a `SKILL.md` file, in the
[AgentSkills](https://agentskills.io/specification) format. Add the
folder the same way. Such a skill usually has no triggers: the agent sees
its name and description, and opens it when it decides it needs it.

To stop using a skill:

```bash
certo skills remove my-style --global
```

Official skills can't be removed.

## Download a skill from git

```bash
certo skills add github:anthropics/skills skills/algorithmic-art --global
certo skills enable algorithmic-art --global
```

A skill from git is treated as untrusted:

- **Downloaded is not on.** It stays off until you run `enable`. Read its
  files first.
- **Exact and checked.** The folder's `skills.lock.json` records the
  source, the exact commit, the license and a hash of every file. A skill
  whose files changed on disk is skipped; `certo skills sync` restores it.
- **Licenses.** Certo recognises a few common open licenses (MIT,
  Apache-2.0, BSD, ISC, MPL-2.0, Unlicense, CC0) from their text. Anything
  else is `unknown`, and `enable` refuses it until you add
  `--accept-unknown-license` after reading the terms. This is a text
  match, not legal advice.
- **Changes turn it off.** If `certo skills update` brings new content or a
  new license, the skill is off again until you enable it.
- Certo never runs a downloaded file, and shows a skill's `` !`command` ``
  as text. But a skill's text can still ask the agent to run its scripts.
  See [Safety](../concepts/safety.md#third-party-skills).

> **Experimental.** Downloading skills from git works and is tested, but
> no downloaded skill has been benchmarked. See
> [Experimental features](../README.md#experimental-features).

## The project's own skills

`AGENTS.md` and `.agents/skills/` at the top of a project are part of the
project: commit them, and other AI tools read them too. Certo gives them
to the agent on every task in that folder, and never changes them.

`AGENTS.md` holds facts every task should know, in plain words:

```markdown
This project uses FastAPI and Poetry.
Run the tests with `poetry run pytest`.
Never edit files under migrations/ by hand.
```

Certo can write it when it starts a task (this replaces the file, and
needs `--project`):

```bash
certo "Add a /health endpoint" --project my-api --agents-md "This project uses FastAPI and Poetry."
```

A `CLAUDE.md`, `GEMINI.md` or `.cursorrules` file works the same way.
`.agents/skills/` holds skill files, written as above. In a git
repository, the repository's top folder counts too; where both have a
skill of the same name, the folder the agent works in wins.

Because these files are in the folder the agent works in, the agent can
read and change them. Commit them, so you see any change in `git diff`.

## Official skills

Eight lifecycle skills, for every language, each firing on words in the
task:

| Skill | Fires on | Covers |
|---|---|---|
| `repository-discovery` | implement, build, add, create, refactor, migrate, integrate, scaffold, inspect, explore | Find the project's real languages, tools, commands and conventions before assuming any. |
| `requirements-analysis` | feature, requirement, bug, unclear, ambiguous, vague | Pin down the outcome, acceptance criteria, edge cases, and what "verified" means here. |
| `implementation-planning` | refactor, architecture, redesign, restructure, rearchitect | Read the code first, plan the smallest change, avoid unrelated edits. |
| `testing-and-verification` | test, implement, fix, bug | Use the project's own checks, add focused tests, never weaken a test to pass. |
| `debugging-and-failure-repair` | error, fail, failing, failed, traceback, exception, crash, broken | Start from the real error, find the cause, make a small fix, run the check again. |
| `security-review` | auth, authentication, authorization, login, password, token, secret, credential, session, payment, api, database, deploy, production | Secrets, injection, access control, unsafe defaults, data leaks. |
| `documentation-and-operational-readiness` | api, config, configuration, setup, install, deploy, cli, endpoint | Keep the README, setup steps and configuration docs in step with the change. |
| `completion-and-release-readiness` | release, deploy, production, ship, launch, pull request, PR | A final review before finishing; never claim success while a check fails. |

And four more: `pytest-conventions`, `commit-conventions`,
`fastapi-conventions`, and `pin-dependencies` (which fires when the agent
edits `pyproject.toml` or `requirements*.txt`).

The agent is also told to apply the lifecycle skills when they fit even if
no trigger word appears, and to skip them for trivial changes.

## Moving from the old folders

Until version 0.1.22, your skills lived in `./skills` (`CERTO_SKILLS_DIR`)
and downloaded ones in `./third_party_skills/`, both relative to the
folder `certo` runs from, where they could end up in a repository. Certo
still reads them until the next release, and a run prints a line asking
you to move them:

```bash
certo skills add skills/my-style.md --global
certo skills add github:OWNER/REPO skills/NAME --global
```

`certo-admin skills` manages only the old folder, and goes away in the
next release too.

## Good to know

- **Skills guide; they don't check.** Whether the result works is still
  decided by Certo's own checks.
- **Every skill that fires costs context.** Prefer narrow triggers, and
  check with `certo skills list --task`.
- **Docker execution (experimental):** skills haven't been checked under
  `--execution docker`.

## Related

- [Commands: `certo skills`](../reference/commands.md#certo-skills)
- [Add custom tools](add-custom-tools.md)
- [Work on an existing project](work-on-an-existing-project.md)
