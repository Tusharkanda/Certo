"""The escalation loop in runner.py, with fake conversations and fake models:
no SDK run loop, no network."""

from __future__ import annotations

import uuid
from contextlib import nullcontext
from types import SimpleNamespace
from typing import ClassVar

import pytest
from model_file_helpers import write_model_files
from openhands.sdk import ConversationExecutionStatus
from openhands.sdk.conversation.exceptions import ConversationRunError
from openhands.sdk.llm.exceptions.types import LLMRateLimitError

from certo import runner
from certo.config import Config
from certo.verification import CheckOutcome
from certo.escalation import handoff_task, ladder_from_models, resolve_ladder
from certo.model_catalog import load_model_catalog

_REAL_AGENT_CHANGED_FILES = runner._agent_changed_files


@pytest.fixture(autouse=True)
def _agent_changes_a_file(monkeypatch):
    """The fake conversations here never touch the folder. Count every run
    as changing a file, so they keep testing what they test; the tests of
    `unchanged` put the real check back."""
    monkeypatch.setattr(runner, "_agent_changed_files", lambda *_a: True)


_CATALOG = """
models:
  - name: local
    model: ollama/qwen3-coder:30b
    base_url: http://localhost:11434
    ratings: {code: 2, cost: 5}
  - name: mid
    model: openai/gpt-5.6-luna
    api_key: k
    ratings: {code: 4, cost: 4}
  - name: strong
    model: anthropic/claude-sonnet-5-5
    api_key: k
    ratings: {code: 5, cost: 2}
escalation:
  ladders:
    default:
      - model: local
        retries: 1
      - model: mid
        reasoning_effort: low
      - model: strong
    careful:
      escalate_on_acceptance_failed: true
      rungs: [{model: local}, {model: strong}]
"""


def _cfg(tmp_path, **overrides) -> Config:
    base = {
        "model": "openai/not-used",
        "api_key": "env-key",
        "base_url": None,
        "workspace": str(tmp_path),
        "max_iterations": 10,
        "confirm_mode": "never",
        "execution": "local",
    }
    base.update(overrides)
    return Config(**base)


def _ladder(tmp_path, name=None, models=None):
    catalog = load_model_catalog(*write_model_files(tmp_path, _CATALOG))
    if models is not None:
        return ladder_from_models(catalog, models)
    return resolve_ladder(catalog, name)


def _check(name="pytest", status="failed", output="E   assert 2 == 3"):
    return CheckOutcome(
        name=name,
        command="pytest -q",
        primary=True,
        status=status,
        exit_code=1 if status == "failed" else 0,
        project_root="/x",
        summary=f"{name} {status}",
        output=output,
    )


def _outcome(verdict, retries=0, checks=()):
    return runner.TaskOutcome(
        verification_state=verdict,
        completion_contract=runner.CompletionContract(
            goal="task", acceptance_criteria=[], verification_checks=[], limitations=[]
        ),
        checks=tuple(checks),
        retries_used=retries,
    )


class _Conversation:
    instances: ClassVar[list] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.state = SimpleNamespace(
            execution_status=ConversationExecutionStatus.FINISHED, events=[]
        )
        _Conversation.instances.append(self)

    def set_confirmation_policy(self, policy):
        self.policy = policy


def _provider_failure():
    return ConversationRunError(uuid.uuid4(), LLMRateLimitError("slow down"))


@pytest.fixture
def fake_run(monkeypatch, tmp_path):
    """Script each rung: (verdict | exception, cost, files to write)."""
    _Conversation.instances = []
    calls: list[dict] = []
    script: list[tuple] = []

    monkeypatch.setattr(runner, "Conversation", _Conversation)
    monkeypatch.setattr(
        runner, "build_agent", lambda cfg, **kw: {"usage_id": kw["usage_id"], "cfg": cfg}
    )
    monkeypatch.setattr(runner, "build_workspace", lambda cfg: nullcontext("the-workspace"))

    def phases(conversation, cfg, emit, task, *args, **_kwargs):
        deadline, first_message = args[2], args[6]
        calls.append({"cfg": cfg, "first_message": first_message, "deadline": deadline})
        verdict, cost, files = script[len(calls) - 1]
        conversation.cost = cost
        for name, text in files.items():
            (tmp_path / name).write_text(text)
        if isinstance(verdict, BaseException):
            raise verdict
        checks = (_check(),) if verdict not in ("verified", "inconclusive") else ()
        return _outcome(verdict, retries=1, checks=checks)

    def metrics(conversation):
        agent = conversation.kwargs["agent"]
        return {
            agent["usage_id"]: {
                "accumulated_cost": conversation.cost,
                "accumulated_token_usage": {
                    "model": agent["cfg"].model,
                    "prompt_tokens": 1000,
                    "completion_tokens": 100,
                },
            }
        }

    monkeypatch.setattr(runner, "_run_stream_task_phases", phases)
    monkeypatch.setattr(runner, "_per_model_metrics", metrics)
    return SimpleNamespace(calls=calls, script=script)


def _run(tmp_path, ladder, **kwargs):
    emitted: list = []
    progress: list[str] = []
    cfg = kwargs.pop("cfg", None) or _cfg(tmp_path)
    outcome = runner.stream_task(
        "Build the thing",
        cfg=cfg,
        on_message=emitted.append,
        ladder=ladder,
        on_progress=progress.append,
        **kwargs,
    )
    return outcome, progress


def test_verified_on_the_first_rung_stops_there(tmp_path, fake_run):
    fake_run.script[:] = [("verified", 0.0, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert outcome.verification_state == "verified"
    assert outcome.final_rung == 1
    assert [r.name for r in outcome.rungs] == ["local"]
    assert len(_Conversation.instances) == 1
    assert progress[0].startswith("Escalation: explicit ladder 'default', 3 rung(s):")


@pytest.mark.parametrize(
    "verdict", ["retry_exhausted", "no_progress", "timed_out", "incomplete", "stuck"]
)
def test_these_verdicts_climb_to_the_next_rung(tmp_path, fake_run, verdict):
    fake_run.script[:] = [(verdict, 0.0, {}), ("verified", 0.01, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert [r.verdict for r in outcome.rungs] == [verdict, "verified"]
    assert outcome.final_rung == 2
    assert outcome.verification_state == "verified"
    assert (
        f"Certo: local ended {verdict} after 1 fix attempt; escalating to mid (rung 2 of 3)."
        in progress
    )


@pytest.mark.parametrize(
    "verdict", ["budget_exhausted", "confirmation_required", "acceptance_failed"]
)
def test_these_verdicts_stop_the_climb(tmp_path, fake_run, verdict):
    fake_run.script[:] = [(verdict, 0.0, {"app.py": "x"})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path))

    assert outcome.verification_state == verdict
    assert len(outcome.rungs) == 1


def test_inconclusive_with_files_climbs_and_asks_for_tests(tmp_path, fake_run):
    """The 0.1.17 escalation run: a local model wrote the module, then its
    test file as a tool call written as text, so nothing could be checked
    and the next model was never asked."""
    fake_run.script[:] = [("inconclusive", 0.0, {"app.py": "x"}), ("verified", 0.0, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert [r.verdict for r in outcome.rungs] == ["inconclusive", "verified"]
    assert outcome.verification_state == "verified"
    assert (
        "Certo: local ended inconclusive: it changed files, but nothing could be checked; "
        "escalating to mid (rung 2 of 3)." in progress
    )
    handoff = fake_run.calls[1]["first_message"]
    assert "left nothing Certo could check" in handoff
    assert "add tests that check what the task asks" in handoff


def test_two_inconclusive_rungs_in_a_row_stop_the_climb(tmp_path, fake_run):
    # Nothing in the project can be checked (a plain HTML page, a missing
    # tool): climbing on would pay for every rung and face the same blank.
    fake_run.script[:] = [
        ("inconclusive", 0.0, {"index.html": "x"}),
        ("inconclusive", 0.0, {"style.css": "y"}),
        ("verified", 0.0, {}),
    ]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert outcome.verification_state == "inconclusive"
    assert len(outcome.rungs) == 2
    assert any("two models in a row left nothing Certo could check" in p for p in progress)
    assert outcome.model_decisions[-1].kind == "escalation_stop"


def test_acceptance_failed_climbs_when_the_ladder_opts_in(tmp_path, fake_run):
    fake_run.script[:] = [("acceptance_failed", 0.0, {}), ("verified", 0.0, {})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path, "careful"))
    assert [r.name for r in outcome.rungs] == ["local", "strong"]


def test_the_last_rung_verdict_is_final(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {}), ("stuck", 0, {}), ("retry_exhausted", 0, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert outcome.verification_state == "retry_exhausted"
    assert outcome.final_rung == 3
    assert progress[-1] == (
        "Certo: strong ended retry_exhausted; escalation stops: it was the last rung (3 of 3)."
    )


def test_each_rung_is_a_fresh_conversation_with_its_own_model_and_settings(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {}), ("verified", 0, {})]
    _run(tmp_path, _ladder(tmp_path))

    first, second = _Conversation.instances
    assert first is not second
    assert first.kwargs["workspace"] == second.kwargs["workspace"] == "the-workspace"
    assert first.kwargs["agent"]["usage_id"] == "certo:rung1:local"
    assert second.kwargs["agent"]["usage_id"] == "certo:rung2:mid"
    rung1, rung2 = (c["cfg"] for c in fake_run.calls)
    assert (rung1.model, rung1.api_key, rung1.base_url) == (
        "ollama/qwen3-coder:30b",
        None,
        "http://localhost:11434",
    )
    assert rung1.max_verify_retries == 1  # the rung's own retries
    assert rung2.model == "openai/gpt-5.6-luna"
    assert rung2.reasoning_effort == "low"  # the rung's own reasoning effort
    assert rung2.max_verify_retries == 2  # CERTO_MAX_VERIFY_RETRIES


def test_the_time_budget_is_shared_by_every_rung(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {}), ("verified", 0, {})]
    _run(tmp_path, _ladder(tmp_path))
    assert fake_run.calls[0]["deadline"] == fake_run.calls[1]["deadline"]


def test_a_spent_time_budget_stops_the_climb(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path), cfg=_cfg(tmp_path, max_task_seconds=0))

    assert outcome.verification_state == "no_progress"
    assert "time budget (CERTO_MAX_TASK_SECONDS=0) is spent" in progress[-1]


def test_the_cost_cap_stops_the_climb(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0.5, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path), cfg=_cfg(tmp_path, max_task_cost=0.4))

    assert len(outcome.rungs) == 1
    assert "the cost so far, $0.5000, has reached CERTO_MAX_TASK_COST=0.4" in progress[-1]


def test_unknown_prices_count_as_zero_for_the_cost_cap(tmp_path, fake_run):
    # A cloud model reports tokens but no cost: unknown, counted as 0.
    fake_run.script[:] = [("no_progress", 0.0, {}), ("verified", 0.0, {})]
    ladder = _ladder(tmp_path, models=["mid", "strong"])
    outcome, _ = _run(tmp_path, ladder, cfg=_cfg(tmp_path, max_task_cost=0.1))
    assert len(outcome.rungs) == 2
    assert outcome.rungs[0].cost_known is False


def test_a_local_rung_is_free_not_unknown(tmp_path, fake_run):
    fake_run.script[:] = [("verified", 0.0, {})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path))
    assert outcome.rungs[0].cost_known is True


def test_a_provider_failure_moves_to_the_next_rung(tmp_path, fake_run):
    fake_run.script[:] = [(_provider_failure(), 0, {}), ("verified", 0, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert outcome.verification_state == "verified"
    first = outcome.rungs[0]
    assert first.verdict is None
    assert first.failure == "LLMRateLimitError: slow down"
    assert (
        "Certo: local failed: the provider refused the request (out of credit, or rate "
        "limited) (LLMRateLimitError); escalating to mid (rung 2 of 3)." in progress
    )
    handoff = fake_run.calls[1]["first_message"]
    assert "stopped at a provider error before it created or changed any file" in handoff
    assert "couldn't finish it" not in handoff
    assert "Result: provider or run failure (LLMRateLimitError: slow down)" in handoff
    assert handoff_task(handoff) == "Build the thing"


def test_a_provider_failure_on_the_last_rung_is_raised(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {}), ("stuck", 0, {}), (_provider_failure(), 0, {})]
    with pytest.raises(ConversationRunError):
        _run(tmp_path, _ladder(tmp_path))


def test_any_other_run_error_is_raised_at_once_locally(tmp_path, fake_run):
    fake_run.script[:] = [(ConversationRunError(uuid.uuid4(), RuntimeError("bug")), 0, {})]
    with pytest.raises(ConversationRunError):
        _run(tmp_path, _ladder(tmp_path))
    assert len(fake_run.calls) == 1


def test_in_docker_any_run_error_ends_the_rung(tmp_path, fake_run):
    fake_run.script[:] = [
        (ConversationRunError(uuid.uuid4(), RuntimeError("server said ERROR")), 0, {}),
        ("verified", 0, {}),
    ]
    outcome, _ = _run(tmp_path, _ladder(tmp_path), cfg=_cfg(tmp_path, execution="docker"))
    assert [r.verdict for r in outcome.rungs] == [None, "verified"]


def test_the_handoff_message_is_built_from_facts(tmp_path, fake_run):
    (tmp_path / "README.md").write_text("old")
    fake_run.script[:] = [
        ("no_progress", 0, {"wordle.py": "def score(): ...", "README.md": "new text"}),
        ("verified", 0, {}),
    ]
    _run(tmp_path, _ladder(tmp_path))

    message = fake_run.calls[1]["first_message"]
    assert fake_run.calls[0]["first_message"] is None  # rung 1 gets the task itself
    assert "This summary was written by Certo from what it recorded, not by a model." in message
    assert "- Model: local (ollama/qwen3-coder:30b)" in message
    assert "- Result: no_progress" in message
    assert "- Fix attempts after failed checks: 1" in message
    assert "- Files it created: wordle.py" in message
    assert "- Files it changed: README.md" in message
    assert "- Checks failing when it stopped: pytest (`pytest -q`)" in message
    assert "The task:\n\nBuild the thing" in message
    assert "E   assert 2 == 3" in message  # the real failing output


def test_a_third_rung_hears_about_both_earlier_ones(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {}), ("stuck", 0, {}), ("verified", 0, {})]
    _run(tmp_path, _ladder(tmp_path))
    message = fake_run.calls[2]["first_message"]
    assert "- Model: mid (openai/gpt-5.6-luna)" in message
    assert "- Earlier models on this task: local: no_progress" in message


def test_interactive_yes_climbs_and_shows_the_cost(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0.0, {}), ("verified", 0.02, {})]
    questions: list[str] = []

    def answer(question):
        questions.append(question)
        return True

    outcome, _ = _run(
        tmp_path, _ladder(tmp_path), cfg=_cfg(tmp_path, interactive=True), on_escalate=answer
    )

    assert len(outcome.rungs) == 2
    assert questions[0].startswith("local couldn't finish (no_progress). Try mid next?")
    assert "Cost so far: $0.0000. mid:" in questions[0]


def test_interactive_no_stops_with_the_current_verdict(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {})]
    outcome, progress = _run(
        tmp_path,
        _ladder(tmp_path),
        cfg=_cfg(tmp_path, interactive=True),
        on_escalate=lambda q: False,
    )
    assert outcome.verification_state == "no_progress"
    assert "you chose not to try the next model" in progress[-1]


def test_without_interactive_the_question_is_never_asked(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {}), ("verified", 0, {})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path), on_escalate=lambda q: pytest.fail("asked"))
    assert len(outcome.rungs) == 2


def test_per_rung_results_and_the_combined_summary(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0.0, {}), ("verified", 0.25, {})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path))

    first, second = outcome.rungs
    assert (first.number, first.name, first.retries_used) == (1, "local", 1)
    assert first.summary.total_tokens == 1100
    assert second.cost == 0.25
    assert outcome.run_summary.total_cost == 0.25
    assert {m.model for m in outcome.run_summary.models} == {
        "ollama/qwen3-coder:30b",
        "openai/gpt-5.6-luna",
    }


def test_the_escalate_setting_resolves_the_ladder_itself(tmp_path, fake_run):
    list_path, models_path = write_model_files(tmp_path, _CATALOG)
    fake_run.script[:] = [("verified", 0, {})]
    cfg = _cfg(
        tmp_path,
        model_selection="escalate",
        escalation_ladder="careful",
        models_file=models_path,
        models_list_file=list_path,
    )
    outcome, progress = _run(tmp_path, None, cfg=cfg)
    assert progress[0].startswith("Escalation: explicit ladder 'careful'")
    assert outcome.final_rung == 1


def test_a_single_model_run_never_escalates(tmp_path, fake_run, monkeypatch):
    monkeypatch.setattr(
        runner, "_stream_escalation", lambda *a, **k: pytest.fail("escalation without a ladder")
    )
    fake_run.script[:] = [("no_progress", 0, {})]
    outcome = runner.stream_task("Build the thing", cfg=_cfg(tmp_path))

    assert outcome.verification_state == "no_progress"
    assert outcome.rungs == ()
    assert outcome.final_rung is None
    assert len(_Conversation.instances) == 1


# --- visibility --------------------------------------------------------------------


def test_model_decisions_records_the_ladder_every_climb_and_the_stop(tmp_path, fake_run):
    fake_run.script[:] = [(_provider_failure(), 0, {}), ("no_progress", 0, {}), ("verified", 0, {})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path))

    assert [d.kind for d in outcome.model_decisions] == [
        "ladder",
        "climb_provider_failure",
        "climb_quality_failure",
        "escalation_stop",
    ]
    text = (tmp_path / "MODEL_DECISIONS.md").read_text()
    assert "Explicit ladder 'default' from models_list.yaml." in text
    assert "Ladder (explicit ladder 'default'):" in text
    assert "- **local** (capability" in text
    assert (
        "local failed: the provider refused the request (out of credit, or rate limited) "
        "(LLMRateLimitError); escalating to mid (rung 2 of 3). "
        "The error: LLMRateLimitError: slow down" in text
    )
    assert "mid ended no_progress after 1 fix attempt; escalating to strong (rung 3 of 3)." in text
    assert "strong ended verified, which doesn't escalate." in text


def test_model_decisions_explains_a_derived_ladder(tmp_path, fake_run):
    fake_run.script[:] = [("verified", 0, {})]
    _run(tmp_path, _derived(tmp_path))
    text = (tmp_path / "MODEL_DECISIONS.md").read_text()
    assert "Derived from the active models' ratings: capability is the sum" in text
    assert "except 'cost' (usually reasoning + precision + code)" in text
    assert "Task profile:" not in text


def _derived(tmp_path):
    from certo.escalation import derive_ladder

    return derive_ladder(load_model_catalog(*write_model_files(tmp_path, _CATALOG)))


def test_model_decisions_is_written_even_when_a_rung_raises(tmp_path, fake_run):
    fake_run.script[:] = [(ConversationRunError(uuid.uuid4(), RuntimeError("bug")), 0, {})]
    with pytest.raises(ConversationRunError):
        _run(tmp_path, _ladder(tmp_path))
    assert "Explicit ladder 'default'" in (tmp_path / "MODEL_DECISIONS.md").read_text()


def test_each_rung_gets_its_own_artifacts_folder(tmp_path, fake_run):
    import json

    artifacts = tmp_path / "artifacts"
    fake_run.script[:] = [("no_progress", 0, {}), ("verified", 0.1, {})]
    _run(tmp_path, _ladder(tmp_path), cfg=_cfg(tmp_path, artifacts_dir=str(artifacts)), run_id="r1")

    top = json.loads((artifacts / "_unscoped" / "r1" / "metadata.json").read_text())
    assert top["model_selection"] == "escalate"
    assert top["verification_state"] == "verified"
    assert [(r["name"], r["verdict"], r["final"]) for r in top["rungs"]] == [
        ("local", "no_progress", False),
        ("mid", "verified", True),
    ]
    rung_dirs = sorted(p.name for p in (artifacts / "_unscoped" / "r1" / "rungs").iterdir())
    assert rung_dirs == ["1-local", "2-mid"]
    first = json.loads(
        (artifacts / "_unscoped" / "r1" / "rungs" / "1-local" / "metadata.json").read_text()
    )
    assert (first["model"], first["verification_state"]) == (
        "ollama/qwen3-coder:30b",
        "no_progress",
    )
    assert (artifacts / "_unscoped" / "r1" / "rungs" / "2-mid" / "transcript.json").is_file()


def test_the_per_rung_summary_lines(tmp_path, fake_run):
    from certo.escalation import format_rung_lines

    fake_run.script[:] = [("no_progress", 0.0, {}), ("verified", 0.25, {})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path))
    lines = format_rung_lines(outcome.rungs, outcome.final_rung)

    assert lines[0] == "Rungs:"
    assert lines[1].startswith("  1. local (ollama/qwen3-coder:30b): no_progress, 1 fix attempt, ")
    assert lines[1].endswith(", 1,100 tokens, $0.0000")
    assert lines[2].endswith(", 1,100 tokens, $0.2500")
    assert lines[3] == "Final result from rung 2 (mid)."


# --- regressions: nothing changes without --escalate ------------------------------


def test_auto_model_ranking_ignores_the_escalation_section(tmp_path):
    from certo.model_catalog import classify_task, rank_candidates

    ranked = []
    for folder, text in (
        ("with", _CATALOG),
        ("without", _CATALOG[: _CATALOG.index("escalation:")]),
    ):
        (tmp_path / folder).mkdir()
        catalog = load_model_catalog(*write_model_files(tmp_path / folder, text))
        weights = classify_task("Build the thing", catalog).weights
        ranked.append([e.name for e in rank_candidates(catalog, weights)])
    assert ranked[0] == ranked[1]


def test_auto_model_runs_one_conversation_and_never_escalates(tmp_path, fake_run, monkeypatch):
    monkeypatch.setattr(
        runner, "_stream_escalation", lambda *a, **k: pytest.fail("escalation in auto mode")
    )
    list_path, models_path = write_model_files(tmp_path, _CATALOG)
    fake_run.script[:] = [("no_progress", 0, {})]
    cfg = _cfg(
        tmp_path, model_selection="auto", models_file=models_path, models_list_file=list_path
    )

    outcome = runner.stream_task("Build the thing", cfg=cfg)

    assert outcome.rungs == ()
    assert len(_Conversation.instances) == 1
    assert outcome.model_decisions[0].kind == "initial"


# --- unchanged ---------------------------------------------------------------------


def test_unchanged_climbs_and_the_next_model_is_told_nothing_changed(tmp_path, fake_run):
    fake_run.script[:] = [("unchanged", 0, {}), ("verified", 0, {"app.py": "x"})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path))

    assert outcome.verification_state == "verified"
    assert [r.verdict for r in outcome.rungs] == ["unchanged", "verified"]
    handoff = fake_run.calls[1]["first_message"]
    assert "changed no file, even when Certo asked it to" in handoff
    assert "couldn't finish it" not in handoff


def test_two_rungs_in_a_row_unchanged_stop_the_climb(tmp_path, fake_run):
    fake_run.script[:] = [("unchanged", 0, {}), ("unchanged", 0, {}), ("verified", 0, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert outcome.verification_state == "unchanged"
    assert len(outcome.rungs) == 2
    assert any("two models in a row did no work" in p for p in progress)
    assert outcome.model_decisions[-1].kind == "escalation_stop"


def test_unchanged_after_another_verdict_still_climbs(tmp_path, fake_run):
    fake_run.script[:] = [("no_progress", 0, {}), ("unchanged", 0, {}), ("verified", 0, {})]
    outcome, _ = _run(tmp_path, _ladder(tmp_path))

    assert [r.verdict for r in outcome.rungs] == ["no_progress", "unchanged", "verified"]


# --- inconclusive with no file changed -------------------------------------------


def test_inconclusive_with_no_file_changed_climbs(tmp_path, fake_run):
    """The 0.1.15 benchmark: a model that writes its tool calls as text ends
    the run with an empty folder. A stronger model may do the task."""
    fake_run.script[:] = [("inconclusive", 0, {}), ("verified", 0, {"app.py": "x"})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert [r.verdict for r in outcome.rungs] == ["inconclusive", "verified"]
    assert outcome.verification_state == "verified"
    assert (
        "Certo: local ended inconclusive without changing a file; escalating to mid "
        "(rung 2 of 3)." in progress
    )
    handoff = fake_run.calls[1]["first_message"]
    assert "created or changed no file, so there was nothing for Certo to check" in handoff
    assert "couldn't finish it" not in handoff


def test_no_work_twice_in_a_row_stops_the_climb_whatever_the_verdicts(tmp_path, fake_run):
    fake_run.script[:] = [("inconclusive", 0, {}), ("unchanged", 0, {}), ("verified", 0, {})]
    outcome, progress = _run(tmp_path, _ladder(tmp_path))

    assert outcome.verification_state == "unchanged"
    assert len(outcome.rungs) == 2
    assert any("two models in a row did no work" in p for p in progress)
    assert outcome.model_decisions[-1].kind == "escalation_stop"
