# Skill tasks

Benchmark tasks for measuring Certo's official skills, in the same shape
as the bundled task set (`task.md`, `hidden_tests/`, `reference/`). They
are kept apart from the bundled set so its version and results stay
comparable. Each task needs what a skill is meant to bring, without
asking for it in words.

Run them with `tasks_dir: skill-tasks` in a bench file, and compare an
arm with the skill against one with `skills_off`.

- `hangman-cli`: a terminal game. For `testable-interactive-apps`: the
  task never asks for tests, so a run is `verified` only when the agent
  makes the game testable and tests it.
