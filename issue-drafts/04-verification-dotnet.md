# Verification for C#/.NET projects

**Context.** Certo checks Python, Node, Go, Rust and Java projects by running their own tests. A .NET project is detected as unknown today, so its verdict is always `inconclusive`. I'd welcome .NET support, following the pattern the other languages use.

**How Certo could detect it and what it could run** (a suggestion; check it against real projects):
- Detect by a `*.sln` or `*.csproj` file. Unlike every marker today, these are file *patterns*, not fixed names, so `detect_project()` needs a small change to match by extension.
- Main check: `dotnet test`. Extra check: `dotnet build` (if `test` is the main check, the build is already part of it; decide whether a separate build check adds anything).
- Missing `dotnet`: the checks are `unavailable`.
- Check what `dotnet test` does in a solution with no test project. If it succeeds with nothing tested, that is the same gap Node has with `node --test` (see the separate issue about it); treat it the same way.

**What done looks like.**
- `certo verify` on a small C#/.NET project with passing tests ends `verified`; with a failing test, `failed`; without the tool installed, `inconclusive` with a note naming the missing tool.
- The plan tests in `tests/custom_tools/test_run_tests_tool.py` don't need C#/.NET installed (fake the tool lookup, like the Go tests do). A test that really runs the tool skips when it isn't installed, as `CONTRIBUTING.md` describes.
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
uv run certo verify path/to/a/small/dotnet/project
```

**Labels:** help wanted, verification
