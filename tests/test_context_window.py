import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from certo import context_window as cw


def test_input_limit_keeps_a_reserve_for_the_answer():
    assert cw.input_limit(131072) == 98304
    assert cw.input_limit(32768) == 24576
    assert cw.input_limit(20000) == 16384  # never under the SDK's minimum


def test_is_ollama():
    assert cw.is_ollama("ollama/qwen3.8:27b") and cw.is_ollama("ollama_chat/x")
    assert not cw.is_ollama("anthropic/claude-haiku-5-5")


class _FakeOllama(BaseHTTPRequestHandler):
    loaded: list = []

    def log_message(self, *_args):
        pass

    def _reply(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).loaded.append(body["model"])
        self._reply({"done": True, "done_reason": "load"})

    def do_GET(self):
        if self.path == "/api/version":
            self._reply({"version": "0.12.6"})
            return
        models = [{"name": m, "model": m, "context_length": 32768} for m in type(self).loaded]
        self._reply({"models": models})


@pytest.fixture
def fake_ollama(monkeypatch):
    _FakeOllama.loaded = []
    server = HTTPServer(("127.0.0.1", 0), _FakeOllama)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_the_window_is_read_from_ollama_after_loading_the_model(fake_ollama):
    from importlib import reload

    fresh = reload(cw)  # the real function, not conftest's stub
    try:
        assert fresh.ollama_context_tokens("ollama/qwen3.8:27b", fake_ollama, 5) == 32768
        assert _FakeOllama.loaded == ["qwen3.8:27b"]
        fresh.ollama_context_tokens("ollama/qwen3.8:27b", fake_ollama, 5)
        assert _FakeOllama.loaded == ["qwen3.8:27b"]  # cached
    finally:
        reload(cw)


def test_an_unreachable_server_gives_none():
    from importlib import reload

    fresh = reload(cw)
    try:
        assert fresh.ollama_context_tokens("ollama/x", "http://127.0.0.1:9", 2) is None
    finally:
        reload(cw)


def test_the_version_is_read_from_ollama(fake_ollama):
    from importlib import reload

    fresh = reload(cw)
    try:
        assert fresh.ollama_version(fake_ollama) == "0.12.6"
        assert fresh.ollama_version("http://127.0.0.1:9", 2) is None
    finally:
        reload(cw)


def test_server_address_is_host_and_port_only():
    assert cw.server_address("http://user:secret@gpu-box:11434/v1") == "gpu-box:11434"
    assert cw.server_address(None) == "localhost:11434"
    assert cw.server_address("https://ollama.example.com") == "ollama.example.com"
