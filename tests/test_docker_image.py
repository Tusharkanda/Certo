"""The agent-server image copies only the files `certo.custom_tools` needs
(docker/agent-server.Dockerfile). A module those tools import but the image
doesn't copy fails only inside a real container, which no test starts."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"


def _certo_imports(path: Path) -> set[Path]:
    """The certo modules `path` imports at its top level, as files."""
    found: set[Path] = set()
    package = path.parent
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            base = package
            for _ in range(node.level - 1):
                base = base.parent
            parts = node.module.split(".") if node.module else []
        elif node.module and node.module.split(".")[0] == "certo":
            base, parts = _SRC, node.module.split(".")
        else:
            continue
        target = base.joinpath(*parts)
        for candidate in (target.with_suffix(".py"), target / "__init__.py"):
            if candidate.is_file():
                found.add(candidate)
    return found


def test_the_image_copies_every_module_the_custom_tools_import():
    dockerfile = (_REPO / "docker" / "agent-server.Dockerfile").read_text(encoding="utf-8")
    copied = re.findall(r"^COPY (src/certo/\S*) ", dockerfile, re.MULTILINE)
    assert copied

    def is_copied(path: Path) -> bool:
        rel = path.relative_to(_REPO).as_posix()
        return any(rel == c or (c.endswith("/") and rel.startswith(c)) for c in copied)

    todo = list((_SRC / "certo" / "custom_tools").glob("*.py"))
    seen: set[Path] = set()
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        todo.extend(_certo_imports(path))
    missing = sorted(p.relative_to(_REPO).as_posix() for p in seen if not is_copied(p))
    assert missing == []
