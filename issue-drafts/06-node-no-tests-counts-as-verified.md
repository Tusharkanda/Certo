# A Node project with no test files counts as `verified`

**Context.** Certo trusts a check's exit code. `node --test` exits 0 when it finds no test files, so a project with `"test": "node --test"` and no tests at all ends `verified`, with nothing tested. It's a documented limitation ([Verification by language](https://github.com/alessioricco/certo/blob/main/docs/reference/verification-by-language.md#node-in-detail)), and a `verified` that tested nothing is exactly what Certo exists to prevent.

You can see it with Node 22 in an empty folder:

```console
$ echo '{"name":"x","scripts":{"test":"node --test"}}' > package.json
$ CI=true npm test
...
# tests 0
# pass 0
# fail 0
...
$ echo $?
0
```

**What done looks like.**
- When `npm test` is the main check and the output shows that no test ran, the check is `skipped` and the verdict is `inconclusive`. That's what Python already does when pytest collects no tests (exit code 5, `PYTEST_NO_TESTS_COLLECTED`).
- A project with at least one test is unchanged.
- One question to settle in the pull request: when `npm run build` is the main check, `npm test` runs as an extra check, and an extra check can only turn a pass into a failure. Should "no tests ran" there change anything? My suggestion is to leave that case alone in this issue, and add a note under the verdict instead.
- The two docs pages that describe the gap are updated: [Verification by language](https://github.com/alessioricco/certo/blob/main/docs/reference/verification-by-language.md#node-in-detail) ("Known gap") and the matching line in [Known limitations](https://github.com/alessioricco/certo/blob/main/docs/README.md#known-limitations).

**Where to start.**
- `src/certo/custom_tools/run_tests_tool.py`: `_node_plan()` builds the Node checks; `execute_check()` turns a command's result into a `CheckOutcome`.
- `CheckSpec` in the same file: `skip_exit_codes` (the pytest case) and `missing_tool_markers` (text in the output that changes the result) show the two existing ways a check's status is decided from more than "exit 0 means passed". Detecting no tests probably needs a third, based on the output of a successful run.
- What to look for: `node --test` prints `# tests 0` with its TAP reporter (the one used without a terminal). Check what Jest, Vitest and Mocha do with no tests: some already exit with an error, so only the ones that succeed need handling.
- Tests: `tests/custom_tools/test_run_tests_tool.py`, next to `test_node_plan_uses_test_as_primary_when_no_build_script`.

**How to check it.**
```bash
uv run pytest -q                       # no API key needed
uv run certo verify path/to/empty-node-project   # should end inconclusive, not verified
```

**Labels:** help wanted, verification
