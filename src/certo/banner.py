"""The banner `certo "<task>"` prints before a run: the version and the
settings that decide how the run goes, so a wrong model or folder is
seen before the agent starts, not after."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from . import __version__
from .config import Config
from .escalation import ResolvedLadder

_RULE_WIDTH = 60


def _server(base_url: str | None) -> str:
    # Host and port only: a URL can carry a user and password.
    if not base_url:
        return ""
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return f" at {host}" if host else ""


def _model_line(cfg: Config, ladder: ResolvedLadder | None) -> str:
    if ladder is not None:
        names = " → ".join(rung.name for rung in ladder.rungs)
        return f"escalate: {names}"
    if cfg.model_selection == "auto":
        return "auto: picked from the model files for this task"
    return f"{cfg.model}{_server(cfg.base_url)}"


def _duration(seconds: int) -> str:
    minutes, rest = divmod(seconds, 60)
    if minutes and rest:
        return f"{minutes}m {rest}s"
    return f"{minutes} min" if minutes else f"{rest}s"


def format_banner(
    cfg: Config, *, ladder: ResolvedLadder | None = None, project: str | None = None
) -> list[str]:
    title = f"── Certo {__version__} "
    folder = os.path.abspath(cfg.workspace)
    if project:
        folder += f" (project {project})"
    runs_in = "this computer" if cfg.execution == "local" else f"Docker ({cfg.docker_image})"
    if cfg.verify_tests == "never":
        checks = "off (CERTO_VERIFY_TESTS=never)"
    else:
        checks = f"on, up to {cfg.max_verify_retries} fix attempts"
    limits = [_duration(cfg.max_task_seconds), f"{cfg.max_iterations} steps"]
    if cfg.max_task_cost is not None:
        cost = cfg.max_task_cost
        # Cents, unless that would hide part of the limit ($0.004).
        limits.append(f"${cost:.2f}" if round(cost, 2) == cost else f"${cost:g}")
    lines = [
        title + "─" * max(0, _RULE_WIDTH - len(title)),
        f"  Model    {_model_line(cfg, ladder)}",
        f"  Folder   {folder}",
        f"  Runs on  {runs_in}",
        f"  Checks   {checks}",
        f"  Limits   {' · '.join(limits)}",
    ]
    modes = []
    if cfg.interactive:
        modes.append("interactive: the agent may ask you questions")
    if cfg.confirm_mode == "always":
        modes.append("confirm: you approve every action")
    if modes:
        lines.append(f"  Mode     {'; '.join(modes)}")
    lines.append("─" * _RULE_WIDTH)
    return lines
