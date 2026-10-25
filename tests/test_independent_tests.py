"""independent_tests.py tests: the writer's result, running the tests on a
finished project, and the report line. A fake writer, no model."""

from __future__ import annotations

from pathlib import Path

from certo import independent_tests as it
from certo.bench_tasks import HIDDEN_DIR_NAME
from certo.config import Config

TEST_ADD = "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def _cfg() -> Config:
    return Config(
        model="openai/gpt-4o",
        api_key="key",
        base_url=None,
        workspace=".",
        max_iterations=10,
        confirm_mode="never",
        execution="local",
    )


def _writer(files: dict[str, str]):
    seen = {}

    def run(prompt: str, scratch: Path, cfg: Config, usage_id: str) -> dict[str, dict]:
        seen.update(prompt=prompt, scratch=scratch, usage_id=usage_id)
        seen["project_files"] = sorted(
            p.relative_to(scratch / it.PROJECT_DIR).as_posix()
            for p in (scratch / it.PROJECT_DIR).rglob("*")
            if p.is_file()
        )
        for name, text in files.items():
            (scratch / it.TESTS_DIR / name).write_text(text)
        return {usage_id: {"accumulated_cost": 0.001}}

    return run, seen


def _project(tmp_path: Path, make_venv, body: str) -> Path:
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "calc.py").write_text(body)
    make_venv(workspace)
    return workspace


def test_the_writer_gets_the_task_and_an_empty_project_for_a_new_one(tmp_path):
    run, seen = _writer({"test_add.py": TEST_ADD})

    written = it.write_tests("Write calc.add(a, b).", _cfg(), tmp_path / "tests", run_writer=run)

    assert seen["prompt"].endswith("Write calc.add(a, b).\n")
    assert "Never guess a name neither of them gives." in seen["prompt"]
    assert seen["project_files"] == []
    assert written.folder == (tmp_path / "tests").resolve() / it.TESTS_DIR
    assert f"directly in the folder {written.folder} (an absolute" in seen["prompt"]
    assert seen["usage_id"] == it.WRITER_USAGE_ID
    assert written.runnable and written.language == "python"
    assert written.files == ("test_add.py",) and set(written.hashes) == {"test_add.py"}
    assert written.metrics == {it.WRITER_USAGE_ID: {"accumulated_cost": 0.001}}


def test_the_writer_reads_a_copy_of_the_project_before_the_build(tmp_path):
    project = tmp_path / "project"
    (project / "ledger").mkdir(parents=True)
    (project / "ledger" / "money.py").write_text("def parse_amount(text): ...\n")
    for skipped in (".git", ".venv", "node_modules", ".certo"):
        (project / skipped).mkdir()
        (project / skipped / "x.txt").write_text("not for the writer")
    (project / "big.bin").write_bytes(b"0" * (it._MAX_FILE_BYTES + 1))
    run, seen = _writer({"test_money.py": "def test_x():\n    assert True\n"})

    it.write_tests(
        "Fix parse_amount.", _cfg(), tmp_path / "scratch", project=project, run_writer=run
    )

    assert seen["project_files"] == ["ledger/money.py"]
    assert (project / "ledger" / "money.py").exists()  # a copy; the project is untouched


def test_no_tests_when_the_task_names_nothing_to_call(tmp_path):
    run, _ = _writer({it.NO_TESTS_FILE: "The task names no function or command.\n"})

    written = it.write_tests("Make a fun game.", _cfg(), tmp_path / "t", run_writer=run)
    result = it.run_independent_tests(written, tmp_path)

    assert not written.runnable
    assert result.status == "none"
    assert it.report_line(result) == (
        "Independent tests: none (The task names no function or command.)."
    )


def test_files_certo_cant_run_and_an_empty_folder_say_so(tmp_path):
    ruby, _ = _writer({"calc_test.rb": "# ruby"})
    nothing, _ = _writer({})

    assert (
        "aren't tests Certo can run"
        in it.write_tests("t", _cfg(), tmp_path / "a", run_writer=ruby).reason
    )
    assert it.write_tests("t", _cfg(), tmp_path / "b", run_writer=nothing).reason == (
        "the test writer wrote nothing"
    )


def test_a_writer_failure_is_reported_not_raised(tmp_path):
    def broken(*_args):
        raise RuntimeError("provider down")

    written = it.write_tests("t", _cfg(), tmp_path / "t", run_writer=broken)

    assert not written.runnable
    assert written.reason == "the test writer stopped with an error (RuntimeError: provider down)"


def test_correct_work_passes_and_the_project_is_left_as_it_was(tmp_path, project_venv):
    run, _ = _writer({"test_add.py": TEST_ADD})
    written = it.write_tests("t", _cfg(), tmp_path / "t", run_writer=run)
    workspace = _project(tmp_path, project_venv, "def add(a, b):\n    return a + b\n")

    result = it.run_independent_tests(written, workspace)

    assert result.status == "passed", result.output
    assert not (workspace / HIDDEN_DIR_NAME).exists()
    assert it.report_line(result).startswith("Independent tests: passed, ")
    assert "(written from the task by openai/gpt-4o; report only)." in it.report_line(result)


def test_wrong_work_fails(tmp_path, project_venv):
    run, _ = _writer({"test_add.py": TEST_ADD})
    written = it.write_tests("t", _cfg(), tmp_path / "t", run_writer=run)
    workspace = _project(tmp_path, project_venv, "def add(a, b):\n    return a - b\n")

    result = it.run_independent_tests(written, workspace)

    assert result.status == "failed"
    assert it.report_line(result).startswith("Independent tests: failed, ")


def test_a_test_changed_after_writing_is_not_run(tmp_path):
    run, _ = _writer({"test_add.py": TEST_ADD})
    written = it.write_tests("t", _cfg(), tmp_path / "t", run_writer=run)
    (written.folder / "test_add.py").write_text("def test_add():\n    assert True\n")

    result = it.run_independent_tests(written, tmp_path)

    assert result.status == "error"
    assert it.report_line(result) == (
        "Independent tests: couldn't run (test_add.py changed after it was written; not run)."
    )


def test_failing_tests_are_named_for_each_test_tool():
    output = "\n".join(
        [
            "FAILED new_tests/test_money.py::test_bad_parentheses - assert 1 == 2",
            "not ok 3 - transfers are left out",
            "--- FAIL: TestLoanLimit (0.00s)",
            "test due_dates ... FAILED",
            "test fines ... ok",
        ]
    )
    result = it.IndependentTestsResult("failed", "4 failed", "m", output)

    assert it.failing_tests(result) == [
        "new_tests/test_money.py::test_bad_parentheses",
        "transfers are left out",
        "TestLoanLimit",
        "due_dates",
    ]
    assert it.failing_tests(result, limit=2) == it.failing_tests(result)[:2]


def test_failing_pytest_names_start_at_the_tests_folder():
    # Seen in a replay: a project under /var (a symlink to /private/var).
    line = (
        "FAILED ../../../../var/folders/T/certo-x/project/.certo_hidden_tests/"
        "test_durations.py::test_parse_parts - assert False"
    )
    result = it.IndependentTestsResult("failed", "1 failed", "m", line)

    assert it.failing_tests(result) == [".certo_hidden_tests/test_durations.py::test_parse_parts"]


# --- Several sets, each by its own writer, voting -------------------------


def test_each_set_has_its_own_writer_folder_and_usage_id(tmp_path):
    used = []

    def run(prompt: str, scratch: Path, cfg: Config, usage_id: str) -> dict[str, dict]:
        used.append((scratch, usage_id))
        (scratch / it.TESTS_DIR / "test_add.py").write_text(TEST_ADD)
        return {usage_id: {"accumulated_cost": 0.001}}

    written = it.write_test_sets("Write calc.add.", _cfg(), tmp_path, count=3, run_writer=run)

    assert [w.folder for w in written.sets] == [
        tmp_path.resolve() / f"set{k}" / it.TESTS_DIR for k in (1, 2, 3)
    ]
    assert sorted(u for _, u in used) == [
        "certo:test-writer",
        "certo:test-writer-2",
        "certo:test-writer-3",
    ]
    assert written.usage_ids == ["certo:test-writer", "certo:test-writer-2", "certo:test-writer-3"]
    assert set(written.metrics) == set(written.usage_ids)  # every writer's cost
    assert written.scratch == tmp_path.resolve()


def test_most_sets_must_fail():
    assert [it.failing_sets_needed(n) for n in (1, 2, 3, 4, 5)] == [1, 2, 2, 3, 3]


def _sets(tmp_path: Path, statuses: list[str], monkeypatch) -> it.IndependentTestsResult:
    sets = tuple(
        it.WrittenTests(folder=tmp_path / f"set{k}", model="m", language="python")
        for k in range(1, len(statuses) + 1)
    )
    results = {
        w.folder: it.IndependentTestsResult(s, f"{s} summary", "m", f"FAILED t.py::t{k}")
        for k, (w, s) in enumerate(zip(sets, statuses, strict=True), start=1)
    }
    monkeypatch.setattr(it, "run_independent_tests", lambda w, ws, r=None: results[w.folder])
    return it.run_test_sets(it.TestSets(scratch=tmp_path, sets=sets), tmp_path)


def test_two_of_three_failing_sets_fail(tmp_path, monkeypatch):
    result = _sets(tmp_path, ["failed", "passed", "failed"], monkeypatch)

    assert (result.status, result.summary) == ("failed", "2 of 3 sets failed")
    assert it.report_line(result) == (
        "Independent tests: failed, 2 of 3 sets failed (written from the task by m; report only)."
    )
    assert it.set_lines(result) == [
        "set 1: failed (failed summary): t.py::t1",
        "set 2: passed (passed summary): t.py::t2",
        "set 3: failed (failed summary): t.py::t3",
    ]


def test_one_failing_set_of_three_is_split(tmp_path, monkeypatch):
    result = _sets(tmp_path, ["passed", "failed", "passed"], monkeypatch)

    assert (result.status, result.summary) == ("split", "1 of 3 sets failed")


def test_a_set_that_couldnt_run_doesnt_count_as_failing(tmp_path, monkeypatch):
    result = _sets(tmp_path, ["error", "passed", "failed"], monkeypatch)

    assert result.status == "split"
    passed = _sets(tmp_path, ["none", "passed", "passed"], monkeypatch)
    assert (passed.status, passed.summary) == ("passed", "2 of 3 sets passed")


def test_no_set_ran_reports_the_first_reason(tmp_path, monkeypatch):
    result = _sets(tmp_path, ["none", "none", "error"], monkeypatch)

    assert result.status == "none" and len(result.sets) == 3
    assert it.report_line(result) == "Independent tests: none (none summary)."


def test_one_set_reports_as_before(tmp_path, monkeypatch):
    result = _sets(tmp_path, ["failed"], monkeypatch)

    assert result.sets == () and it.set_lines(result) == []
    assert it.report_line(result).startswith("Independent tests: failed, failed summary")


def test_a_strict_report_line_isnt_report_only(tmp_path, monkeypatch):
    result = _sets(tmp_path, ["failed", "failed", "passed"], monkeypatch)

    line = it.report_line(result, strict=True)
    assert line.startswith("Independent tests: failed, 2 of 3 sets failed (written from the task")
    assert "report only" not in line
