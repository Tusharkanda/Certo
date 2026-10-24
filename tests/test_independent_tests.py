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
