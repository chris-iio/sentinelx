"""Tests for the repo-native dev-server helper contract."""
from __future__ import annotations

import importlib.util
import json
import socket
import sys
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SCRIPT = Path("tools/dev_server.py")
BOUNDARY_SCRIPT = Path("tools/runtime_state_boundary.py")


def load_dev_server_module():
    module_name = "dev_server_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_boundary_module():
    module_name = "runtime_state_boundary_for_dev_server_tests"
    spec = importlib.util.spec_from_file_location(module_name, BOUNDARY_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _SilentHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A003
        return


class HealthyHandler(_SilentHandler):
    def do_GET(self):  # noqa: N802
        payload = json.dumps(
            {"service": "sentinelx", "status": "ok", "ready": True}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class SecretBearingHealthHandler(_SilentHandler):
    def do_GET(self):  # noqa: N802
        payload = json.dumps(
            {
                "service": "sentinelx",
                "status": "ok",
                "ready": True,
                "provider_key": "sk-local-dev-should-never-appear",
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class SlowHealthHandler(_SilentHandler):
    def do_GET(self):  # noqa: N802
        time.sleep(0.2)
        payload = json.dumps(
            {"service": "sentinelx", "status": "ok", "ready": True}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except BrokenPipeError:
            pass


@contextmanager
def running_server(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def test_repo_root_discovery_and_paths_stay_under_runtime_boundary():
    dev_server = load_dev_server_module()
    boundary = load_boundary_module()

    repo_root = dev_server.discover_repo_root()
    paths = dev_server.dev_server_paths(repo_root)
    classification = boundary.classify_paths([str(paths.status_path)], repo_root)[0]

    assert repo_root == Path.cwd().resolve()
    assert paths.runtime_dir.relative_to(repo_root).as_posix() == ".gsd/runtime/dev-server"
    assert paths.status_path.relative_to(repo_root).as_posix() == ".gsd/runtime/dev-server/status.json"
    assert paths.logs_dir.relative_to(repo_root).as_posix() == ".gsd/runtime/dev-server/logs"
    assert ".bg-shell" not in str(paths.runtime_dir)
    assert classification.classification == "transient"


def test_status_round_trip_and_empty_runtime_default(tmp_path: Path):
    dev_server = load_dev_server_module()
    paths = dev_server.dev_server_paths(tmp_path)

    default_status = dev_server.read_status_or_default(paths)
    assert default_status.status == "stopped"
    assert default_status.host == dev_server.DEFAULT_HOST
    assert default_status.port == dev_server.DEFAULT_PORT
    assert default_status.probe is None

    stored_status = dev_server.DevServerStatus(
        status="running",
        host="127.0.0.1",
        port=5001,
        updated_at="2026-04-25T11:00:00Z",
        restart_count=2,
        pid=12345,
        log_path=".gsd/runtime/dev-server/logs/server.log",
        started_at="2026-04-25T10:59:00Z",
        last_failure_at=None,
        last_failure_reason=None,
        probe=dev_server.HealthProbeResult(
            status="healthy",
            checked_at="2026-04-25T11:00:00Z",
            url="http://127.0.0.1:5001/api/health",
            http_status=200,
            detail=None,
        ),
    )

    destination = dev_server.write_status(paths, stored_status)
    loaded_status = dev_server.load_status(paths)

    assert destination == paths.status_path
    assert loaded_status == stored_status
    assert json.loads(paths.status_path.read_text(encoding="utf-8"))["status"] == "running"


def test_load_status_rejects_partial_unknown_invalid_port_and_non_local_host_payloads(tmp_path: Path):
    dev_server = load_dev_server_module()
    paths = dev_server.dev_server_paths(tmp_path)
    paths.runtime_dir.mkdir(parents=True)

    paths.status_path.write_text('{"status": "running"}\n', encoding="utf-8")
    with pytest.raises(dev_server.StatusContractError, match="missing required keys"):
        dev_server.load_status(paths)

    paths.status_path.write_text(
        json.dumps(
            {
                "status": "mystery",
                "host": "127.0.0.1",
                "port": 5000,
                "updated_at": "2026-04-25T11:00:00Z",
                "restart_count": 0,
                "probe": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(dev_server.StatusContractError, match="Unknown dev-server status"):
        dev_server.load_status(paths)

    paths.status_path.write_text(
        json.dumps(
            {
                "status": "running",
                "host": "0.0.0.0",
                "port": 5000,
                "updated_at": "2026-04-25T11:00:00Z",
                "restart_count": 0,
                "pid": 101,
                "log_path": ".gsd/runtime/dev-server/logs/server.log",
                "started_at": "2026-04-25T10:59:00Z",
                "probe": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(dev_server.StatusContractError, match="Host must stay local"):
        dev_server.load_status(paths)

    with pytest.raises(dev_server.StatusContractError, match="between 1 and 65535"):
        dev_server.normalize_port(0)
    with pytest.raises(dev_server.StatusContractError, match="between 1 and 65535"):
        dev_server.normalize_port(70000)


def test_load_status_rejects_malformed_json(tmp_path: Path):
    dev_server = load_dev_server_module()
    paths = dev_server.dev_server_paths(tmp_path)
    paths.runtime_dir.mkdir(parents=True)
    paths.status_path.write_text('{"status": ', encoding="utf-8")

    with pytest.raises(dev_server.StatusContractError, match="malformed JSON"):
        dev_server.load_status(paths)


def test_probe_health_reports_healthy_for_exact_contract():
    dev_server = load_dev_server_module()

    with running_server(HealthyHandler) as port:
        result = dev_server.probe_health(port=port, timeout=0.2)

    assert result.status == "healthy"
    assert result.http_status == 200
    assert result.detail is None
    assert result.url == f"http://127.0.0.1:{port}/api/health"


def test_probe_health_reports_refused_timeout_and_malformed():
    dev_server = load_dev_server_module()

    refused_result = dev_server.probe_health(port=unused_port(), timeout=0.05)
    assert refused_result.status == "refused"

    with running_server(SlowHealthHandler) as slow_port:
        timeout_result = dev_server.probe_health(port=slow_port, timeout=0.05)
    assert timeout_result.status == "timeout"

    with running_server(SecretBearingHealthHandler) as malformed_port:
        malformed_result = dev_server.probe_health(port=malformed_port, timeout=0.2)
    assert malformed_result.status == "malformed"
    assert malformed_result.detail == "unexpected health payload"


def test_refresh_status_reports_running_starting_stale_and_crashed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dev_server = load_dev_server_module()
    paths = dev_server.dev_server_paths(tmp_path)

    base = dev_server.DevServerStatus(
        status="running",
        host="127.0.0.1",
        port=5001,
        updated_at="2026-04-25T11:00:00Z",
        restart_count=0,
        pid=12345,
        log_path=".gsd/runtime/dev-server/logs/server.log",
        started_at="2026-04-25T10:59:00Z",
        last_failure_at=None,
        last_failure_reason=None,
        probe=None,
    )
    dev_server.write_status(paths, base)

    monkeypatch.setattr(dev_server, "process_is_running", lambda pid: True)
    monkeypatch.setattr(
        dev_server,
        "probe_health",
        lambda host, port, timeout=0.5: dev_server.HealthProbeResult(
            status="healthy",
            checked_at="2026-04-25T11:01:00Z",
            url="http://127.0.0.1:5001/api/health",
            http_status=200,
            detail=None,
        ),
    )
    running = dev_server.refresh_status(paths)
    assert running.status == "running"

    fresh_start = dev_server.DevServerStatus(
        status="starting",
        host="127.0.0.1",
        port=5001,
        updated_at="2026-04-25T11:00:00Z",
        restart_count=0,
        pid=12345,
        log_path=".gsd/runtime/dev-server/logs/server.log",
        started_at=dev_server.utc_now(),
        last_failure_at=None,
        last_failure_reason=None,
        probe=None,
    )
    dev_server.write_status(paths, fresh_start)
    monkeypatch.setattr(
        dev_server,
        "probe_health",
        lambda host, port, timeout=0.5: dev_server.HealthProbeResult(
            status="refused",
            checked_at="2026-04-25T11:01:00Z",
            url="http://127.0.0.1:5001/api/health",
            http_status=None,
            detail="connection refused",
        ),
    )
    starting = dev_server.refresh_status(paths, starting_grace_seconds=5.0)
    assert starting.status == "starting"

    dev_server.write_status(paths, base)
    monkeypatch.setattr(
        dev_server,
        "probe_health",
        lambda host, port, timeout=0.5: dev_server.HealthProbeResult(
            status="timeout",
            checked_at="2026-04-25T11:01:00Z",
            url="http://127.0.0.1:5001/api/health",
            http_status=None,
            detail="request timed out",
        ),
    )
    stale = dev_server.refresh_status(paths, starting_grace_seconds=0.0)
    assert stale.status == "stale"
    assert stale.last_failure_reason == "Health probe timed out."

    dev_server.write_status(paths, base)
    monkeypatch.setattr(dev_server, "process_is_running", lambda pid: False)
    monkeypatch.setattr(
        dev_server,
        "probe_health",
        lambda host, port, timeout=0.5: dev_server.HealthProbeResult(
            status="refused",
            checked_at="2026-04-25T11:01:00Z",
            url="http://127.0.0.1:5001/api/health",
            http_status=None,
            detail="connection refused",
        ),
    )
    crashed = dev_server.refresh_status(paths)
    assert crashed.status == "crashed"
    assert "Managed child pid 12345 is no longer running" in crashed.last_failure_reason


def test_status_command_surfaces_malformed_state_contract(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    dev_server = load_dev_server_module()
    paths = dev_server.dev_server_paths(tmp_path)
    paths.runtime_dir.mkdir(parents=True)
    paths.status_path.write_text('{"status": ', encoding="utf-8")

    exit_code = dev_server.main([
        "--repo-root",
        str(tmp_path),
        "status",
        "--format",
        "json",
    ])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "crashed"
    assert "malformed JSON" in payload["last_failure_reason"]
    assert payload["status_path"] == ".gsd/runtime/dev-server/status.json"


def test_start_rejects_non_local_host_before_launch(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    dev_server = load_dev_server_module()

    exit_code = dev_server.main([
        "--repo-root",
        str(tmp_path),
        "start",
        "--host",
        "0.0.0.0",
        "--port",
        "5001",
        "--format",
        "json",
    ])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["status"] == "crashed"
    assert "Host must stay local" in payload["last_failure_reason"]
