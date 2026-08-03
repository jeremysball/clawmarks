import json
import socket
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


def test_server_header_does_not_leak_python_version(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), cs.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz") as resp:
            server_header = resp.headers["Server"]
            assert server_header == "clawmarks"
            assert "Python" not in server_header
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
        # tailscale_ip() must not be consulted when CLAWMARKS_HOST is set: point it at an
        # unreachable address so the test only passes if the env var actually wins.
        monkeypatch.setattr(cs, "tailscale_ip", lambda: "192.0.2.1")
        monkeypatch.setattr(cs, "DEFAULT_PORT", port)
        assert cs.healthcheck() == 0
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_healthcheck_fails_with_nothing_listening(monkeypatch):
    # Bind to a real port, then close it: guaranteed-free at the moment of capture, unlike a
    # hardcoded low port that may or may not have something else listening on it.
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    monkeypatch.setenv("CLAWMARKS_HOST", "127.0.0.1")
    monkeypatch.setattr(cs, "DEFAULT_PORT", port)
    assert cs.healthcheck() == 1
