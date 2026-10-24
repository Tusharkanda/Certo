"""OpenHands plugins that would reach a run from outside the project.

The SDK loads "ambient" plugins into every local conversation, with no
switch to turn it off (ARCHITECTURE.md, SDK gotchas): the user's own
(`~/.agents/plugins/`, `~/.openhands/plugins/`, the installed ones) and the
project's (`.agents/plugins/`, `.openhands/plugins/`, in the workspace and
at the root of the git repository around it). A plugin can add skills, MCP
servers and hooks, outside Certo's official / third-party separation.

So Certo checks before a run, with the SDK's own discovery functions, and
refuses to start when one would load (DECISIONS.md): a user plugin always;
a project plugin from outside the folder of a project Certo generates
(inside `CERTO_PROJECTS_DIR`). An existing folder keeps its repository's
plugins, as it keeps its `AGENTS.md`. Docker runs aren't checked: the
agent-server in the container has no user plugins, and sees only the
mounted project.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ForeignPlugin:
    name: str
    path: str
    user: bool  # from the user's folders, not the project's


def foreign_plugins(
    workspace: str | Path | None, projects_dir: str | Path | None = None
) -> list[ForeignPlugin]:
    """The plugins the SDK would load into a run in `workspace` that don't
    belong to it. `workspace` may not exist yet (a new `--project`); None
    checks the user's plugins only (`certo bench`, whose workspaces are new
    temporary folders)."""
    from openhands.sdk.plugin import load_project_plugins, load_user_plugins

    found = [ForeignPlugin(p.name, p.path, user=True) for p in load_user_plugins()]
    if workspace is None or projects_dir is None:
        return found
    root = Path(workspace).resolve()
    if root.is_relative_to(Path(projects_dir).resolve()):
        found += [
            ForeignPlugin(p.name, p.path, user=False)
            for p in load_project_plugins(root)
            if not Path(p.path).resolve().is_relative_to(root)
        ]
    return found


def refusal(found: list[ForeignPlugin]) -> str:
    """Why the run doesn't start, and what to do, for the error message."""
    lines = [
        "OpenHands plugins would be loaded into this run, and Certo doesn't use them "
        "(they can add skills, tools and hooks that Certo hasn't checked):"
    ]
    for plugin in found:
        where = "your user folder" if plugin.user else "a repository above the project"
        lines.append(f"  - {plugin.name}: {plugin.path} (from {where})")
    lines.append(
        "Move or rename these folders while you use Certo, or put the skills you want "
        "in Certo's own skills (certo skills add). See docs/troubleshooting.md, "
        '"OpenHands plugins would be loaded into this run".'
    )
    return "\n".join(lines)
