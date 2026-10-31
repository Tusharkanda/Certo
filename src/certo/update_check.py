"""Tell the user, in one line, when a newer Certo is on PyPI.

`start()` decides whether to check at all (an interactive terminal, not
CI, not turned off, a released version) and starts a background thread
that asks PyPI for the latest version, at most once a day: the answer is
kept in a small file in the user's cache folder. `UpdateCheck.notice()`
returns the line to print at the end of the command, or None. A failed
or slow request shows nothing, and never slows a run.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from collections.abc import Callable, Mapping

from . import __version__

PYPI_URL = "https://pypi.org/pypi/certo/json"
CHECK_EVERY_SECONDS = 24 * 60 * 60
_REQUEST_TIMEOUT_SECONDS = 2.0
# How long the end of a command waits for a check still running.
_NOTICE_WAIT_SECONDS = 0.5
_OFF = ("0", "false", "no", "off")


def cache_path(environ: Mapping[str, str] | None = None) -> str:
    """`$XDG_CACHE_HOME/certo/update-check.json`, else
    `~/.cache/certo/update-check.json`, on every platform."""
    environ = os.environ if environ is None else environ
    xdg = (environ.get("XDG_CACHE_HOME") or "").strip()
    base = xdg if os.path.isabs(xdg) else os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "certo", "update-check.json")


def parse_version(text: str) -> tuple[int, ...] | None:
    """`"0.1.27"` -> `(0, 1, 27)`; None for anything else, such as a
    development build (`0.1.27.dev0`)."""
    parts = text.strip().split(".")
    if not parts or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def upgrade_command(prefix: str | None = None) -> str:
    """The command that updates Certo, from where it is installed."""
    where = (sys.prefix if prefix is None else prefix).replace("\\", "/")
    if "/uv/tools/" in where:
        return "uv tool upgrade certo"
    if "/pipx/venvs/" in where:
        return "pipx upgrade certo"
    return "pip install -U certo"


def fetch_latest(timeout: float = _REQUEST_TIMEOUT_SECONDS) -> str | None:
    """The latest version on PyPI, or None when it can't be read."""
    request = urllib.request.Request(PYPI_URL, headers={"User-Agent": f"certo/{__version__}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https URL
            version = json.load(response)["info"]["version"]
    except Exception:  # noqa: BLE001 - offline, PyPI down, odd answer: no notice
        return None
    return version if isinstance(version, str) else None


class UpdateCheck:
    def __init__(
        self,
        current: str,
        path: str,
        fetch: Callable[[], str | None] = fetch_latest,
        now: Callable[[], float] = time.time,
        prefix: str | None = None,
    ) -> None:
        self.current = current
        self.path = path
        self._fetch = fetch
        self._now = now
        self._prefix = prefix
        self.latest: str | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> UpdateCheck:
        cached = self._read_cache()
        if cached is not None:
            self.latest = cached
        else:
            self._thread = threading.Thread(target=self._check, daemon=True)
            self._thread.start()
        return self

    def notice(self, wait: float = _NOTICE_WAIT_SECONDS) -> str | None:
        """The line to show, or None when Certo is up to date or the latest
        version isn't known yet."""
        if self._thread is not None:
            self._thread.join(wait)
        latest, current = parse_version(self.latest or ""), parse_version(self.current)
        if latest is None or current is None or latest <= current:
            return None
        return (
            f"Certo {self.latest} is out (you have {self.current}). "
            f"To update: {upgrade_command(self._prefix)}"
        )

    def _check(self) -> None:
        latest = self._fetch()
        if latest is None:
            return
        self.latest = latest
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"checked_at": self._now(), "latest": latest}, f)
        except OSError:
            pass

    def _read_cache(self) -> str | None:
        """The latest version from a check less than a day old, or None."""
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            checked_at, latest = float(data["checked_at"]), data["latest"]
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if not isinstance(latest, str) or not 0 <= self._now() - checked_at < CHECK_EVERY_SECONDS:
            return None
        return latest


def enabled(environ: Mapping[str, str], interactive: bool) -> bool:
    """Whether to check: an interactive terminal, not CI, not turned off
    with CERTO_UPDATE_CHECK, and a released version of Certo."""
    if not interactive or (environ.get("CI") or "").strip():
        return False
    if (environ.get("CERTO_UPDATE_CHECK") or "").strip().lower() in _OFF:
        return False
    return parse_version(__version__) is not None


def start(environ: Mapping[str, str] | None = None) -> UpdateCheck | None:
    """Start a check when `enabled`, else None. `environ` includes the
    settings files (`.env` and the user settings), so the setting works
    from either."""
    environ = os.environ if environ is None else environ
    try:
        interactive = sys.stderr.isatty()
    except (AttributeError, ValueError):
        interactive = False
    if not enabled(environ, interactive):
        return None
    return UpdateCheck(__version__, cache_path(environ)).start()
