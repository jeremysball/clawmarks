import json
import threading
from http.server import HTTPServer
import urllib.request

from clawmarks import curation_server as cs


def test_healthz_route_returns_ok(monkeypatch, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), cs.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz") as resp:
            assert resp.status == 200
            assert json.loads(resp.read())["status"] == "ok"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_healthcheck_succeeds_against_a_real_listener(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), cs.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        monkeypatch.setenv("CLAWMARKS_HOST", "127.0.0.1")
        monkeypatch.setattr(cs, "DEFAULT_PORT", port)
        assert cs.healthcheck() == 0
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_healthcheck_fails_with_nothing_listening(monkeypatch):
    monkeypatch.setenv("CLAWMARKS_HOST", "127.0.0.1")
    monkeypatch.setattr(cs, "DEFAULT_PORT", 1)  # port 1 requires root; nothing will be listening
    assert cs.healthcheck() == 1
