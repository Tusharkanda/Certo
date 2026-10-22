# Verification for Ruby projects

**Context.** Certo checks Python, Node, Go, Rust and Java projects by running their own tests. A Ruby project is detected as unknown today, so its verdict is always `inconclusive`: Certo can't say whether the agent's work runs. I'd welcome Ruby support, following the pattern the other languages use.

**How Certo could detect it and what it could run** (a suggestion; check it against real projects):
- Detect by `Gemfile`.
- Main check: `bundle exec rspec` when the project uses RSpec (a `spec/` folder or a `.rspec` file), otherwise `bundle exec rake test` when the `Rakefile` defines a test task. With neither, the main check is `unavailable` (no tests set up), like a Node project with no `test` script.
- Extra check: `bundle exec rubocop` when a `.rubocop.yml` exists.
- Missing `ruby` or `bundle`: the checks are `unavailable`.

**What done looks like.**
- `certo verify` on a small Ruby project with passing tests ends `verified`; with a failing test, `failed`; without the tool installed, `inconclusive` with a note naming the missing tool.
- The plan tests in `tests/custom_tools/test_run_tests_tool.py` don't need Ruby installed (fake the tool lookup, like the Go tests do). A test that really runs the tool skips when it isn't installed, as `CONTRIBUTING.md` describes.
- [Verification by language](https://github.com/alessioricco/certo/blob/main/docs/reference/verification-by-language.md) lists the new type in both tables and no longer under "Not covered", and the "Covered languages" line in [Known limitations](https://github.com/alessioricco/certo/blob/main/docs/README.md#known-limitations) includes it. The list of files under "The project type is unknown" in [Verdicts](https://github.com/alessioricco/certo/blob/main/docs/reference/verdicts.md#inconclusive-in-more-detail) and the tools under "Missing tools" in Verification by language name it too.

**Where to start.** Everything is in `src/certo/custom_tools/run_tests_tool.py`:
- `_LANGUAGE_MARKERS`: the files that identify each project type, in priority order. `detect_project()` walks the folder with them.
- `ProjectDetection.language`: the list of known types, in a comment.
- `_go_plan()` and `_rust_plan()`: the simplest examples of a plan. Each returns a list of `CheckSpec`: one `primary=True` check that decides `verified`, extra checks that can only turn a pass into a failure, and an `unavailable_reason` when the tool isn't installed.
- `_node_plan()` and `_npm_test_script()`: how a check is chosen from what the project itself configures. Certo never invents a command the project doesn't set up.
- `CheckSpec.missing_tool_markers`: how `cargo clippy` becomes `unavailable`, not `failed`, when clippy isn't installed.
- `discover_verification_plan()`: where each type is sent to its plan.

Tests: `tests/custom_tools/test_run_tests_tool.py` (see `test_detects_go_via_go_mod`, `test_go_plan_has_test_and_vet` and `test_go_plan_unavailable_without_go_installed`). Docs: [Verification by language](https://github.com/alessioricco/certo/blob/main/docs/reference/verification-by-language.md), which also lists this language under "Not covered" today.

Like Node, Certo shouldn't install the project's dependencies itself; the [Node section of Make your project checkable](https://github.com/alessioricco/certo/blob/main/docs/guides/make-a-project-checkable.md) explains why and how users do it.

**How to check it.**
```bash
uv run pytest -q                 # no API key needed
uv run certo verify path/to/a/small/ruby/project
```

**Labels:** help wanted, verification
