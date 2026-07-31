"""Tests for the repo-native dev-server helper contract."""
from __future__ import annotations

import importlib.util
import inspect
import json
import re
import socket
import sys
import threading
import time
from contextlib import contextmanager, suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.health_contract import HEALTH_PATH, build_health_payload

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


def healthy_payload(status: str = "ok") -> dict:
    checks = {
        "cache": {"status": "ok", "detail": "ok"},
        "history": {"status": "ok", "detail": "ok"},
        "registry": {"status": "ok", "detail": "0/0 providers configured"},
    }
    if status == "degraded":
        checks["cache"] = {"status": "degraded", "detail": "RuntimeError"}
    return build_health_payload(checks)


class HealthyHandler(_SilentHandler):
    def do_GET(self):  # noqa: N802
        payload = json.dumps(healthy_payload()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class DegradedHealthHandler(_SilentHandler):
    def do_GET(self):  # noqa: N802
        payload = json.dumps(healthy_payload("degraded")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class SecretBearingHealthHandler(_SilentHandler):
    def do_GET(self):  # noqa: N802
        payload = json.dumps(
            {**healthy_payload(), "provider_key": "sk-local-dev-should-never-appear"}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class DriftedHealthHandler(_SilentHandler):
    def do_GET(self):  # noqa: N802
        payload = json.dumps({**healthy_payload(), "ready": False}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class SlowHealthHandler(_SilentHandler):
    def do_GET(self):  # noqa: N802
        time.sleep(0.2)
        payload = json.dumps(healthy_payload()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        with suppress(BrokenPipeError):
            self.wfile.write(payload)


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
    source = SCRIPT.read_text(encoding="utf-8")
    helper_source = source[source.index("def discover_repo_root") : source.index("def code_repo_root")]
    assert "*current.parents" not in helper_source
    assert "while candidate is not None" in helper_source


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
            url=f"http://127.0.0.1:5001{HEALTH_PATH}",
            http_status=200,
            detail=None,
        ),
    )

    destination = dev_server.write_status(paths, stored_status)
    loaded_status = dev_server.load_status(paths)

    assert destination == paths.status_path
    assert loaded_status == stored_status
    assert json.loads(paths.status_path.read_text(encoding="utf-8"))["status"] == "running"


def test_dev_server_records_use_slots_to_avoid_instance_dict(tmp_path: Path):
    dev_server = load_dev_server_module()
    paths = dev_server.dev_server_paths(tmp_path)
    probe = dev_server.HealthProbeResult(
        status="healthy",
        checked_at="2026-04-25T11:00:00Z",
        url=f"http://127.0.0.1:5001{HEALTH_PATH}",
        http_status=200,
    )
    status = dev_server.DevServerStatus(
        status="running",
        host="127.0.0.1",
        port=5001,
        updated_at="2026-04-25T11:00:00Z",
        probe=probe,
    )

    assert not hasattr(paths, "__dict__")
    assert not hasattr(probe, "__dict__")
    assert not hasattr(status, "__dict__")


def test_dev_server_static_membership_tables_are_immutable():
    dev_server = load_dev_server_module()

    assert dev_server.VALID_MANAGER_STATUSES == frozenset((
        "stopped",
        "starting",
        "running",
        "stale",
        "crashed",
    ))
    assert dev_server.VALID_PROBE_STATUSES == frozenset((
        "healthy",
        "refused",
        "timeout",
        "malformed",
    ))
    assert dev_server.CONNECTION_REFUSED_ERRNOS == frozenset((61, 111))
    assert dev_server.ACTIVE_MANAGER_STATUSES == frozenset(("starting", "running", "stale"))

    source = SCRIPT.read_text(encoding="utf-8")
    assert "in {61, 111}" not in source
    assert 'status.status in {"starting", "running", "stale"}' not in source


def test_sigkill_timeout_cap_uses_direct_branch():
    dev_server = load_dev_server_module()

    assert dev_server.capped_sigkill_timeout(0.25) == 0.25
    assert dev_server.capped_sigkill_timeout(2.0) == 2.0
    assert dev_server.capped_sigkill_timeout(3.5) == 2.0
    assert "min" not in dev_server.capped_sigkill_timeout.__code__.co_names

    source = SCRIPT.read_text(encoding="utf-8")
    stop_source = source[source.index("def stop_managed_process") : source.index("def serve_child")]
    assert "min(timeout, 2.0)" not in stop_source


def test_dev_server_json_formatter_is_sorted_and_newline_terminated():
    dev_server = load_dev_server_module()

    assert dev_server.format_json_payload({"b": 1, "a": 2}) == '{\n  "a": 2,\n  "b": 1\n}'
    assert dev_server.format_json_payload_line({"b": 1, "a": 2}).endswith("\n")


def test_dev_server_json_call_sites_use_shared_formatter():
    dev_server = load_dev_server_module()

    assert "format_json_payload_line" in dev_server.write_status.__code__.co_names
    assert "format_json_payload" in dev_server.emit_status.__code__.co_names


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


def test_status_payload_key_validation_avoids_key_set_materialization(monkeypatch: pytest.MonkeyPatch):
    """Status/probe payload key validation should scan keys directly."""
    dev_server = load_dev_server_module()

    def fail_set(*_args, **_kwargs):
        raise AssertionError("payload key validation should not materialize set(payload)")

    monkeypatch.setattr("builtins.set", fail_set)

    probe = dev_server.HealthProbeResult.from_payload({
        "status": "healthy",
        "checked_at": "2026-04-25T11:00:00Z",
        "url": f"http://127.0.0.1:5001{HEALTH_PATH}",
        "http_status": 200,
        "detail": None,
    })
    status = dev_server.DevServerStatus.from_payload({
        "status": "running",
        "host": "127.0.0.1",
        "port": 5001,
        "updated_at": "2026-04-25T11:00:00Z",
        "restart_count": 0,
        "pid": 12345,
        "log_path": ".gsd/runtime/dev-server/logs/server.log",
        "started_at": "2026-04-25T10:59:00Z",
        "last_failure_at": None,
        "last_failure_reason": None,
        "probe": probe.to_payload(),
    })

    assert probe.status == "healthy"
    assert status.probe == probe
    assert "validate_payload_keys" in dev_server.HealthProbeResult.from_payload.__func__.__code__.co_names
    assert "validate_payload_keys" in dev_server.DevServerStatus.from_payload.__func__.__code__.co_names


def test_payload_key_validation_reports_unexpected_and_missing_keys() -> None:
    """Shared key validation should preserve status contract error messages."""
    dev_server = load_dev_server_module()

    with pytest.raises(dev_server.StatusContractError, match="Probe payload has unexpected keys: extra"):
        dev_server.HealthProbeResult.from_payload({
            "status": "healthy",
            "checked_at": "2026-04-25T11:00:00Z",
            "url": f"http://127.0.0.1:5001{HEALTH_PATH}",
            "extra": True,
        })

    with pytest.raises(dev_server.StatusContractError, match="Status payload is missing required keys"):
        dev_server.DevServerStatus.from_payload({
            "status": "running",
            "host": "127.0.0.1",
            "port": 5001,
        })


def test_payload_key_formatter_skips_sort_for_single_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Single-key validation errors should avoid sorting work."""
    dev_server = load_dev_server_module()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("single-key validation errors should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    with pytest.raises(dev_server.StatusContractError, match="Probe payload has unexpected keys: extra"):
        dev_server.HealthProbeResult.from_payload({
            "status": "healthy",
            "checked_at": "2026-04-25T11:00:00Z",
            "url": f"http://127.0.0.1:5001{HEALTH_PATH}",
            "extra": True,
        })
    assert dev_server.format_key_names(("extra",)) == "extra"


def test_payload_key_formatter_skips_sort_for_two_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two-key validation errors should sort through direct comparison."""
    dev_server = load_dev_server_module()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("two-key validation errors should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    assert dev_server.format_key_names(("zeta", "alpha")) == "alpha, zeta"
    with pytest.raises(dev_server.StatusContractError, match="Probe payload has unexpected keys: alpha, zeta"):
        dev_server.HealthProbeResult.from_payload({
            "status": "healthy",
            "checked_at": "2026-04-25T11:00:00Z",
            "url": f"http://127.0.0.1:5001{HEALTH_PATH}",
            "zeta": True,
            "alpha": True,
        })


def test_payload_key_formatter_skips_sort_for_three_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Three-key validation errors should sort through direct comparisons."""
    dev_server = load_dev_server_module()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("three-key validation errors should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    assert dev_server.format_key_names(("zeta", "alpha", "middle")) == "alpha, middle, zeta"
    with pytest.raises(dev_server.StatusContractError, match="Probe payload has unexpected keys: alpha, middle, zeta"):
        dev_server.HealthProbeResult.from_payload({
            "status": "healthy",
            "checked_at": "2026-04-25T11:00:00Z",
            "url": f"http://127.0.0.1:5001{HEALTH_PATH}",
            "zeta": True,
            "alpha": True,
            "middle": True,
        })


def test_payload_key_formatter_skips_sort_for_four_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Four-key validation errors should sort through direct comparisons."""
    dev_server = load_dev_server_module()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("four-key validation errors should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    assert dev_server.format_key_names(("zeta", "alpha", "middle", "beta")) == (
        "alpha, beta, middle, zeta"
    )
    assert "key_count == 4" in SCRIPT.read_text(encoding="utf-8")


def test_required_payload_key_scan_uses_direct_known_contract_paths() -> None:
    """Known dev-server payload contracts should not iterate required-key frozensets."""
    dev_server = load_dev_server_module()

    missing_probe: list[str] = []
    dev_server.append_missing_payload_keys(
        missing_probe,
        {"status": "healthy"},
        dev_server._PROBE_PAYLOAD_REQUIRED_KEYS,
    )
    assert missing_probe == ["checked_at", "url"]

    missing_status: list[str] = []
    dev_server.append_missing_payload_keys(
        missing_status,
        {"status": "running", "probe": None},
        dev_server._STATUS_PAYLOAD_REQUIRED_KEYS,
    )
    assert missing_status == ["host", "port", "updated_at", "restart_count"]

    fallback_missing: list[str] = []
    dev_server.append_missing_payload_keys(
        fallback_missing,
        {"alpha": True},
        frozenset(("alpha", "omega")),
    )
    assert fallback_missing == ["omega"]

    helper_source = inspect.getsource(dev_server.append_missing_payload_keys)
    direct_source, fallback_source = helper_source.split("for key in required_keys", 1)
    assert 'required_keys is _PROBE_PAYLOAD_REQUIRED_KEYS' in direct_source
    assert 'missing_keys.append("checked_at")' in direct_source
    assert 'required_keys is _STATUS_PAYLOAD_REQUIRED_KEYS' in direct_source
    assert 'missing_keys.append("restart_count")' in direct_source
    assert "if key not in payload" in fallback_source


def test_payload_key_formatter_reads_short_sequence_length_once() -> None:
    """Short key formatting should not repeat Sequence length work."""
    dev_server = load_dev_server_module()

    class CountedKeys:
        def __init__(self, keys: tuple[str, ...]) -> None:
            self.keys = keys
            self.len_calls = 0

        def __len__(self) -> int:
            self.len_calls += 1
            if self.len_calls > 1:
                raise AssertionError("short key formatter should read length once")
            return len(self.keys)

        def __getitem__(self, index: int) -> str:
            return self.keys[index]

        def __iter__(self):
            raise AssertionError("short key formatter should not iterate")

    single = CountedKeys(("extra",))
    pair = CountedKeys(("zeta", "alpha"))
    triple = CountedKeys(("zeta", "alpha", "middle"))

    assert dev_server.format_key_names(single) == "extra"
    assert dev_server.format_key_names(pair) == "alpha, zeta"
    assert dev_server.format_key_names(triple) == "alpha, middle, zeta"


def test_launch_metadata_error_uses_shared_key_formatter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Launch metadata validation should reuse the shared short-key formatter."""
    dev_server = load_dev_server_module()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("two-field launch metadata errors should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    with pytest.raises(
        dev_server.StatusContractError,
        match="Status 'running' requires launch metadata fields: log_path, pid.",
    ):
        dev_server.DevServerStatus.from_payload({
            "status": "running",
            "host": "127.0.0.1",
            "port": 5001,
            "updated_at": "2026-04-25T11:00:00Z",
            "restart_count": 0,
            "started_at": "2026-04-25T10:59:00Z",
            "probe": None,
        })
    assert "format_key_names" in dev_server.DevServerStatus.from_payload.__func__.__code__.co_names


def test_invalid_host_error_reuses_cached_allowed_host_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid-host validation should not sort the static allowed-host set per failure."""
    dev_server = load_dev_server_module()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("invalid-host errors should reuse cached allowed-host text")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    with pytest.raises(dev_server.StatusContractError, match="Host must stay local"):
        dev_server.normalize_host("0.0.0.0")
    assert dev_server.ALLOWED_LOCAL_HOSTS_DISPLAY == "127.0.0.1, ::1, localhost"
    assert dev_server.ALLOWED_LOCAL_HOSTS == frozenset(("127.0.0.1", "localhost", "::1"))
    assert 'ALLOWED_LOCAL_HOSTS_DISPLAY = ", ".join(sorted(' not in SCRIPT.read_text(encoding="utf-8")


def test_valid_host_normalization_avoids_strip_allocation() -> None:
    """Valid host normalization should trim through index scanning."""
    dev_server = load_dev_server_module()

    class NoStripHost(str):
        def strip(self, chars=None):  # noqa: ANN001
            raise AssertionError("host normalization should not allocate through strip()")

    host = NoStripHost("  localhost  ")

    assert dev_server.normalize_host(host) == "localhost"
    assert dev_server.stripped_text_or_none(NoStripHost(" \n\t ")) is None
    assert "stripped_text_or_none" in dev_server.normalize_host.__code__.co_names
    assert "strip" not in dev_server.stripped_text_or_none.__code__.co_names


def test_load_status_rejects_malformed_json(tmp_path: Path):
    dev_server = load_dev_server_module()
    paths = dev_server.dev_server_paths(tmp_path)
    paths.runtime_dir.mkdir(parents=True)
    paths.status_path.write_text('{"status": ', encoding="utf-8")

    with pytest.raises(dev_server.StatusContractError, match="malformed JSON"):
        dev_server.load_status(paths)


def test_probe_health_reports_healthy_for_schema_contract():
    dev_server = load_dev_server_module()

    with running_server(HealthyHandler) as port:
        result = dev_server.probe_health(port=port, timeout=0.2)

    assert result.status == "healthy"
    assert result.http_status == 200
    assert result.detail is None
    assert result.url == f"http://127.0.0.1:{port}{HEALTH_PATH}"


def test_probe_health_accepts_degraded_ready_schema():
    dev_server = load_dev_server_module()

    with running_server(DegradedHealthHandler) as port:
        result = dev_server.probe_health(port=port, timeout=0.2)

    assert result.status == "healthy"
    assert result.http_status == 200
    assert result.detail is None


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

    with running_server(DriftedHealthHandler) as drifted_port:
        drifted_result = dev_server.probe_health(port=drifted_port, timeout=0.2)
    assert drifted_result.status == "malformed"
    assert drifted_result.detail == "unexpected health payload"


def test_proc_stat_state_parses_without_split_list() -> None:
    """Process state parsing should handle names with spaces without splitting every field."""
    dev_server = load_dev_server_module()

    class NoSplitStat(str):
        def split(self, *_args, **_kwargs):
            raise AssertionError("/proc stat state parsing should not split all fields")

    assert dev_server._proc_stat_state(NoSplitStat("123 (python worker) R 1 2 3")) == "R"
    assert dev_server._proc_stat_state(NoSplitStat("123 (stopped worker) Z 1 2 3")) == "Z"
    assert dev_server._proc_stat_state(NoSplitStat("malformed")) is None
    assert "_proc_stat_state" in dev_server.process_is_running.__code__.co_names


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
            url=f"http://127.0.0.1:5001{HEALTH_PATH}",
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
            url=f"http://127.0.0.1:5001{HEALTH_PATH}",
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
            url=f"http://127.0.0.1:5001{HEALTH_PATH}",
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
            url=f"http://127.0.0.1:5001{HEALTH_PATH}",
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


def test_main_avoids_extra_programmatic_argv_copy(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Programmatic CLI calls should pass argv through without an eager list copy."""
    dev_server = load_dev_server_module()

    exit_code = dev_server.main((
        "--repo-root",
        str(tmp_path),
        "status",
        "--format",
        "json",
    ))
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["status"] == "stopped"
    assert "list(argv)" not in SCRIPT.read_text(encoding="utf-8")


def test_makefile_exposes_supported_dev_server_targets_as_thin_cli_wrappers():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    expected_recipes = {
        "dev-server-start": "$(DEV_SERVER) start --format text",
        "dev-server-status": "$(DEV_SERVER) status --format text",
        "dev-server-restart": "$(DEV_SERVER) restart --format text",
        "dev-server-stop": "$(DEV_SERVER) stop --format text",
    }

    for target, recipe in expected_recipes.items():
        pattern = rf"^{re.escape(target)}:\n\t{re.escape(recipe)}$"
        assert re.search(pattern, makefile, re.MULTILINE), f"missing wrapper for {target}"

    assert "python run.py" not in makefile


def test_readme_documents_the_supported_dev_server_loop_and_transient_runtime_state():
    readme = Path("README.md").read_text(encoding="utf-8")

    for command in (
        "make dev-server-start",
        "make dev-server-status",
        "make dev-server-restart",
        "make dev-server-stop",
    ):
        assert command in readme

    assert "GET /api/health" in readme
    assert "python3 tools/dev_server.py status --format json" in readme
    assert ".gsd/runtime/dev-server/**" in readme
    assert "manager owns `.gsd/runtime/dev-server/**` as transient repo-local state" in readme
    assert "do not manually edit or clean up" in readme
    assert "python run.py" not in readme



def test_runtime_boundary_doc_keeps_dev_server_state_separate_from_bg_shell_and_planning():
    content = Path("docs/runtime-state-boundary.md").read_text(encoding="utf-8")

    assert ".gsd/runtime/dev-server/**" in content
    assert "make dev-server-start" in content
    assert "make dev-server-status" in content
    assert "tools/dev_server.py" in content
    assert ".bg-shell/**" in content
    assert ".planning/**" in content
    assert "should not manually clean or rewrite those files" in content
