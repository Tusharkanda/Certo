"""bench.yaml parsing, validation, and the strategy registry. No model."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from model_file_helpers import write_model_files

from certo import bench_strategies
from certo.bench_config import BenchConfigError, load_bench_config
from certo.bench_strategies import STRATEGIES, AttemptResult, RunContext, run_config
from certo.bench_tasks import load_tasks
from certo.model_files import example_path

_REPO = Path(__file__).resolve().parent.parent

MODELS = """
models:
  - name: local-coder
    model: ollama/qwen3-coder:30b
    base_url: http://localhost:11434
    timeout_seconds: 1200
  - name: cloud
    model: anthropic/claude-sonnet-5-5
    api_key: sk-test
    reasoning_effort: low
  - name: parked
    model: openai/gpt-4o
    api_key: sk-test
    activated: false
"""


def _write(tmp_path: Path, bench: str, models: str = MODELS) -> str:
    list_path, models_path = write_model_files(tmp_path, models)
    path = tmp_path / "bench.yaml"
    path.write_text(f"models_file: {models_path}\nmodels_list_file: {list_path}\n" + bench)
    return str(path)


VALID = """
tasks: all
repeats: 3
arms:
  - name: qwen-local
    strategy: single
    model: local-coder
  - name: sonnet
    strategy: single
    model: cloud
"""


def test_a_valid_file(tmp_path):
    cfg = load_bench_config(_write(tmp_path, VALID))
    assert cfg.repeats == 3
    assert [t.name for t in cfg.tasks] == [t.name for t in load_tasks()]
    assert [(a.name, a.strategy, a.models) for a in cfg.arms] == [
        ("qwen-local", "single", ["local-coder"]),
        ("sonnet", "single", ["cloud"]),
    ]


def test_an_arm_naming_an_inactive_model_is_an_error(tmp_path):
    bench = "arms:\n  - {name: a, strategy: single, model: parked}\n"
    with pytest.raises(BenchConfigError, match="'activated: false'.*Set 'activated: true'"):
        load_bench_config(_write(tmp_path, bench))


def test_models_yaml_warnings_are_kept_for_the_plan(tmp_path):
    models = MODELS.replace("    api_key: sk-test\n    reasoning_effort: low\n", "")
    cfg = load_bench_config(_write(tmp_path, VALID, models))
    assert any("'cloud' has no api_key and no base_url" in w for w in cfg.catalog_warnings)


def test_a_models_yaml_error_stops_the_benchmark(tmp_path):
    models = MODELS + "  - name: cloud\n    model: openai/gpt-4o\n"
    with pytest.raises(BenchConfigError, match="Two models in models_list.yaml are named 'cloud'"):
        load_bench_config(_write(tmp_path, VALID, models))


def test_a_task_list_and_default_repeats(tmp_path):
    bench = "tasks: [page-ranges, slugify]\narms:\n  - {name: a, strategy: single, model: cloud}\n"
    cfg = load_bench_config(_write(tmp_path, bench))
    assert [t.name for t in cfg.tasks] == ["page-ranges", "slugify"]
    assert cfg.repeats == 1


def test_unknown_model_lists_the_catalog_names(tmp_path):
    bench = "arms:\n  - {name: a, strategy: single, model: gpt-9}\n"
    with pytest.raises(BenchConfigError, match="unknown model 'gpt-9'.*has: cloud, local-coder"):
        load_bench_config(_write(tmp_path, bench))


def test_unknown_strategy_lists_the_known_ones(tmp_path):
    bench = "arms:\n  - {name: a, strategy: cascade, models: [cloud]}\n"
    with pytest.raises(
        BenchConfigError, match="unknown strategy 'cascade'.*Known strategies: escalate, single"
    ):
        load_bench_config(_write(tmp_path, bench))


@pytest.mark.parametrize(
    "bench, message",
    [
        ("arms: []\n", "'arms' must be a non-empty list"),
        ("repeats: 0\narms:\n  - {name: a, strategy: single, model: cloud}\n", "'repeats'"),
        ("repeats: true\narms:\n  - {name: a, strategy: single, model: cloud}\n", "'repeats'"),
        ("tasks: [nope]\narms:\n  - {name: a, strategy: single, model: cloud}\n", "unknown task"),
        ("tasks: 3\narms:\n  - {name: a, strategy: single, model: cloud}\n", "'tasks' must be"),
        ("arms:\n  - {name: 'a b', strategy: single, model: cloud}\n", "needs a 'name'"),
        (
            (
                "arms:\n  - {name: a, strategy: single, model: cloud}\n"
                "  - {name: a, strategy: single, model: cloud}\n"
            ),
            "two arms are named 'a'",
        ),
        ("arms:\n  - {name: a, strategy: single}\n", "'model' must be a model name"),
        ("arms:\n  - {name: a, strategy: single, model: cloud, n: 3}\n", "unknown key"),
        ("arms:\n  - {name: a, strategy: single, model: cloud}\nrepeat: 2\n", "unknown key"),
    ],
)
def test_invalid_files_name_the_problem(tmp_path, bench, message):
    with pytest.raises(BenchConfigError, match=message):
        load_bench_config(_write(tmp_path, bench))


def test_missing_bench_file_prints_the_cp_command_for_the_shipped_example(tmp_path):
    # The example ships inside the package (certo/examples/), so the command
    # works after a pip install too.
    target = tmp_path / "bench.yaml"
    with pytest.raises(BenchConfigError) as info:
        load_bench_config(str(target))
    example = example_path("bench.yaml")
    assert Path(example).is_file()
    assert f"cp {example} {target}" in str(info.value)


def test_a_missing_named_models_file(tmp_path):
    path = tmp_path / "bench.yaml"
    path.write_text(f"models_file: {tmp_path / 'nope.yaml'}\narms: []\n")
    with pytest.raises(BenchConfigError, match="'models_file' names .*nope.yaml"):
        load_bench_config(str(path))


def test_no_model_files_says_what_to_copy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "bench.yaml"
    path.write_text("arms: []\n")
    with pytest.raises(BenchConfigError, match="models.yaml.example"):
        load_bench_config(str(path))


def test_the_model_files_are_found_in_the_project_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_model_files(tmp_path, MODELS)
    (tmp_path / "bench.yaml").write_text("arms:\n  - {name: a, strategy: single, model: cloud}\n")
    cfg = load_bench_config("bench.yaml")
    assert cfg.models_list_file == str((tmp_path / "models_list.yaml").resolve())


def test_an_escalation_file_can_be_named(tmp_path):
    list_path, models_path = write_model_files(tmp_path, MODELS)
    escalation = tmp_path / "escalation.yaml"
    escalation.write_text("escalation:\n  max_rungs: 2\n")
    path = tmp_path / "bench.yaml"
    path.write_text(
        f"models_file: {models_path}\nmodels_list_file: {list_path}\n"
        f"escalation_file: {escalation}\n"
        "arms:\n  - {name: a, strategy: single, model: cloud}\n"
    )

    cfg = load_bench_config(str(path))

    assert cfg.escalation_file == str(escalation.resolve())
    assert cfg.model_catalog.escalation.max_rungs == 2


def test_a_missing_escalation_file_is_an_error(tmp_path):
    list_path, models_path = write_model_files(tmp_path, MODELS)
    path = tmp_path / "bench.yaml"
    path.write_text(
        f"models_file: {models_path}\nmodels_list_file: {list_path}\n"
        "escalation_file: ./nope.yaml\narms:\n  - {name: a, strategy: single, model: cloud}\n"
    )

    with pytest.raises(BenchConfigError, match="'escalation_file' names './nope.yaml'"):
        load_bench_config(str(path))


def test_an_arm_naming_a_model_missing_from_models_yaml(tmp_path):
    list_path, models_path = write_model_files(tmp_path, MODELS)
    Path(models_path).write_text("models:\n  - name: cloud\n    api_key: k\n")
    path = tmp_path / "bench.yaml"
    path.write_text(
        f"models_file: {models_path}\nmodels_list_file: {list_path}\n"
        "arms:\n  - {name: a, strategy: single, model: local-coder}\n"
    )
    with pytest.raises(BenchConfigError, match="in models_list.yaml but not in models.yaml"):
        load_bench_config(str(path))


def test_the_shipped_example_is_valid_against_the_shipped_models_example(tmp_path, monkeypatch):
    # Both shipped model examples as they are: copying the three examples
    # must give a benchmark file that loads, once the keys they name are
    # in the settings.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    text = (_REPO / "src/certo/examples/bench.yaml.example").read_text()
    list_path = _REPO / "src/certo/examples/models_list.yaml.example"
    models_path = _REPO / "src/certo/examples/models.yaml.example"
    path = tmp_path / "bench.yaml"
    path.write_text(f"models_file: {models_path}\nmodels_list_file: {list_path}\n" + text)
    cfg = load_bench_config(str(path))
    assert [a.strategy for a in cfg.arms] == ["single", "single", "escalate"]


@pytest.mark.parametrize(
    "bench_file", sorted((_REPO / "docs/benchmark").glob("*.yaml")), ids=lambda p: p.name
)
def test_the_published_benchmark_files_load_against_the_shipped_catalog(tmp_path, bench_file):
    # docs/benchmark/*.yaml reproduce the published results: each must still
    # load once every model of the shipped models_list.yaml is enabled.
    import yaml

    list_path = _REPO / "src/certo/examples/models_list.yaml.example"
    catalog = yaml.safe_load(list_path.read_text())
    models = [
        {"name": m["name"], "base_url": "http://localhost:11434"}
        if m["model"].startswith("ollama/")
        else {"name": m["name"], "api_key": "sk-test"}
        for m in catalog["models"]
    ]
    models_path = tmp_path / "models.yaml"
    models_path.write_text(yaml.safe_dump({"models": models}))
    path = tmp_path / "bench.yaml"
    path.write_text(
        f"models_file: {models_path}\nmodels_list_file: {list_path}\n" + bench_file.read_text()
    )
    cfg = load_bench_config(str(path))
    assert cfg.arms


def test_run_config_takes_everything_from_the_catalog_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("CERTO_LLM_MODEL", "openai/should-not-be-used")
    monkeypatch.setenv("CERTO_LLM_API_KEY", "sk-env")
    cfg = load_bench_config(_write(tmp_path, VALID))
    local = run_config(cfg.catalog["local-coder"], "/ws", "/iso")
    assert (local.model, local.api_key, local.base_url) == (
        "ollama/qwen3-coder:30b",
        None,
        "http://localhost:11434",
    )
    cloud = run_config(cfg.catalog["cloud"], "/ws", "/iso")
    assert (cloud.model, cloud.api_key, cloud.base_url, cloud.reasoning_effort) == (
        "anthropic/claude-sonnet-5-5",
        "sk-test",
        None,
        "low",
    )
    assert cloud.workspace == "/ws"
    assert (local.llm_timeout_seconds, cloud.llm_timeout_seconds) == (1200, 300)
    assert cloud.global_skills_dir.startswith("/iso")
    assert (cloud.model_selection, cloud.confirm_mode, cloud.interactive) == (
        "manual",
        "never",
        False,
    )


def test_single_strategy_runs_the_normal_pipeline_with_the_arm_model(tmp_path):
    cfg = load_bench_config(_write(tmp_path, VALID))
    seen = {}

    def fake_stream(task, *, cfg):
        seen.update(task=task, model=cfg.model)
        return SimpleNamespace(verification_state="verified", retries_used=1, run_summary=None)

    ctx = RunContext("do it", "/ws", cfg.catalog, "/iso", fake_stream)
    result = STRATEGIES["single"].run(ctx, cfg.arms[1].params)
    assert seen == {"task": "do it", "model": "anthropic/claude-sonnet-5-5"}
    assert result == AttemptResult("verified", 1, None, ("cloud",))


def test_a_new_strategy_is_one_registry_entry(tmp_path, monkeypatch):
    """The design promise: adding e.g. best_of needs no change elsewhere."""

    class BestOf:
        name = "best_of"
        description = "test only"

        def parse(self, arm, catalog, where):
            bench_strategies.reject_unknown_keys(arm, {"model", "n"}, where)
            return {
                "model": bench_strategies.model_name(arm, "model", catalog, where),
                "n": arm["n"],
            }

        def models(self, params):
            return [params["model"]]

        def run(self, ctx, params):
            raise NotImplementedError

    monkeypatch.setitem(STRATEGIES, "best_of", BestOf())
    bench = "arms:\n  - {name: b, strategy: best_of, model: cloud, n: 3}\n"
    cfg = load_bench_config(_write(tmp_path, bench))
    assert cfg.arms[0].params == {"model": "cloud", "n": 3}
    assert cfg.arms[0].models == ["cloud"]


# --- strategy: escalate ---------------------------------------------------------------

ESCALATE = """
arms:
  - name: local-then-cloud
    strategy: escalate
    models: [local-coder, cloud]
  - name: derived
    strategy: escalate
"""


def test_escalate_arms_explicit_and_derived(tmp_path):
    cfg = load_bench_config(_write(tmp_path, ESCALATE))
    explicit, derived = cfg.arms
    assert explicit.params == {"models": ["local-coder", "cloud"]}
    assert explicit.models == ["local-coder", "cloud"]
    # A derived arm may use every active model; 'parked' is inactive.
    assert derived.models == ["local-coder", "cloud"]
    assert cfg.model_catalog is not None


@pytest.mark.parametrize(
    ("arm", "message"),
    [
        ("{name: a, strategy: escalate, models: [cloud]}", "at least two models"),
        ("{name: a, strategy: escalate, models: cloud}", "at least two models"),
        ("{name: a, strategy: escalate, models: [cloud, cloud]}", "lists a model twice"),
        ("{name: a, strategy: escalate, models: [cloud, nope]}", "unknown model 'nope'"),
        ("{name: a, strategy: escalate, models: [cloud, parked]}", "'activated: false'"),
        ("{name: a, strategy: escalate, model: cloud}", "unknown key"),
    ],
)
def test_escalate_arm_errors(tmp_path, arm, message):
    with pytest.raises(BenchConfigError, match=message):
        load_bench_config(_write(tmp_path, f"arms:\n  - {arm}\n"))


def _escalation_outcome(final_rung, names):
    from certo.escalation import RungResult

    rungs = tuple(
        RungResult(
            n, name, f"x/{name}", "verified" if n == final_rung else "no_progress", 1, 1.0, None
        )
        for n, name in enumerate(names, start=1)
    )
    return SimpleNamespace(
        verification_state="verified",
        retries_used=0,
        run_summary=None,
        rungs=rungs,
        final_rung=final_rung,
    )


def test_escalate_strategy_runs_an_explicit_ladder(tmp_path):
    cfg = load_bench_config(_write(tmp_path, ESCALATE))
    seen = {}

    def fake_stream(task, *, cfg, ladder):
        seen.update(model=cfg.model, kind=ladder.kind, rungs=[r.name for r in ladder.rungs])
        return _escalation_outcome(2, ["local-coder", "cloud"])

    ctx = RunContext("do it", "/ws", cfg.catalog, "/iso", fake_stream, cfg.model_catalog)
    result = STRATEGIES["escalate"].run(ctx, cfg.arms[0].params)

    assert seen == {
        "model": "ollama/qwen3-coder:30b",
        "kind": "explicit",
        "rungs": ["local-coder", "cloud"],
    }
    assert result.models_used == ("local-coder", "cloud")
    assert result.final_rung == 2
    assert [(r["name"], r["final"]) for r in result.rungs] == [
        ("local-coder", False),
        ("cloud", True),
    ]


def test_escalate_strategy_derives_a_ladder_per_task(tmp_path):
    cfg = load_bench_config(_write(tmp_path, ESCALATE))
    seen = {}

    def fake_stream(task, *, cfg, ladder):
        seen.update(kind=ladder.kind, rungs=[r.name for r in ladder.rungs])
        return _escalation_outcome(1, [ladder.rungs[0].name])

    ctx = RunContext("do it", "/ws", cfg.catalog, "/iso", fake_stream, cfg.model_catalog)
    STRATEGIES["escalate"].run(ctx, cfg.arms[1].params)

    assert seen["kind"] == "derived"
    assert "parked" not in seen["rungs"]


def test_an_arm_on_a_model_whose_key_variable_is_unset_says_which(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    text = (_REPO / "src/certo/examples/bench.yaml.example").read_text()
    list_path = _REPO / "src/certo/examples/models_list.yaml.example"
    models_path = _REPO / "src/certo/examples/models.yaml.example"
    path = tmp_path / "bench.yaml"
    path.write_text(f"models_file: {models_path}\nmodels_list_file: {list_path}\n" + text)

    with pytest.raises(BenchConfigError, match=r"uses \$\{OPENAI_API_KEY\} in models.yaml"):
        load_bench_config(str(path))


def test_a_bench_run_never_gets_the_users_global_skills(tmp_path, monkeypatch):
    from certo import skill_library as lib

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    lib.global_dir().mkdir(parents=True)
    (lib.global_dir() / "my-style.md").write_text("---\nname: my-style\n---\nMine.\n")
    cfg = load_bench_config(_write(tmp_path, VALID))

    run = run_config(cfg.catalog["cloud"], str(tmp_path / "ws"), str(tmp_path / "iso"))

    assert run.global_skills_dir == str(tmp_path / "iso" / "global_skills")
    assert "my-style" not in {s.name for s in lib.collect(run, run.workspace).skills}
