"""Java wrappers follow the execution platform, including Windows batch files."""

import os
from types import SimpleNamespace

import pytest
from test_project_env import _FakeWorkspace, _result

from certo import verification
from certo.project_env import LocalRunner, WorkspaceRunner
from certo.verification import ProjectDetection, discover_verification_plan, run_full_verification


@pytest.mark.parametrize("language, wrapper", [("java-maven", "mvnw"), ("java-gradle", "gradlew")])
@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_local_plan_selects_the_platforms_wrapper(
    tmp_path, monkeypatch, language, wrapper, platform
):
    # Both wrappers are checked in; selecting the Unix file on Windows must fail this test.
    for name in (wrapper, wrapper + ".cmd", wrapper + ".bat"):
        path = tmp_path / name
        path.write_text("exit\n")
        path.chmod(0o755)
    monkeypatch.setattr(verification, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setattr(LocalRunner, "which", lambda self, name: "global-tool")

    [spec] = discover_verification_plan(ProjectDetection(language=language, root=str(tmp_path)))

    suffix = (".cmd" if wrapper == "mvnw" else ".bat") if platform == "win32" else ""
    assert spec.command == [str(tmp_path / (wrapper + suffix)), "test"]


@pytest.mark.parametrize("language, wrapper", [("java-maven", "mvnw"), ("java-gradle", "gradlew")])
def test_docker_plan_uses_unix_wrapper_on_a_windows_host(tmp_path, monkeypatch, language, wrapper):
    for name in (wrapper, wrapper + ".cmd", wrapper + ".bat"):
        path = tmp_path / name
        path.write_text("exit\n")
        path.chmod(0o755)
    monkeypatch.setattr(verification, "sys", SimpleNamespace(platform="win32"))
    runner = WorkspaceRunner(_FakeWorkspace(_result()), str(tmp_path), "/workspace")

    [spec] = discover_verification_plan(
        ProjectDetection(language=language, root=str(tmp_path)), runner=runner
    )

    assert spec.command == [f"/workspace/{wrapper}", "test"]


@pytest.mark.parametrize(
    "language, wrapper, manifest",
    [("java-maven", "mvnw", "pom.xml"), ("java-gradle", "gradlew", "build.gradle")],
)
@pytest.mark.parametrize("exit_code, expected", [(0, "verified"), (1, "failed")])
def test_native_wrapper_runs_from_a_path_with_spaces(
    tmp_path, language, wrapper, manifest, exit_code, expected
):
    root = tmp_path / "project with spaces"
    root.mkdir()
    (root / manifest).touch()
    if os.name == "nt":
        suffix = ".cmd" if wrapper == "mvnw" else ".bat"
        (root / (wrapper + suffix)).write_text(f"@echo off\nexit /b {exit_code}\n")
    else:
        path = root / wrapper
        path.write_text(f"#!/bin/sh\nexit {exit_code}\n")
        path.chmod(0o755)

    result = run_full_verification(str(root))

    assert result.state == expected
    assert result.checks[0].status == ("passed" if exit_code == 0 else "failed")
