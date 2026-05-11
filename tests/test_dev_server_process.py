"""Subprocess proof for the repo-native dev-server lifecycle manager."""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import request

from app.health_contract import HEALTH_PATH, is_valid_health_payload

SCRIPT = Path("tools/dev_server.py").resolve()


def unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def run_cli(runtime_root: Path, *args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT), "--repo-root", str(runtime_root), *args]
    return subprocess.run(
        command,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def parse_json(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout, f"expected JSON output, stderr was: {result.stderr}"
    return json.loads(result.stdout)


def wait_for_status(runtime_root: Path, expected: str, *, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    last_payload: dict | None = None
    while time.monotonic() < deadline:
        result = run_cli(runtime_root, "status", "--format", "json", timeout=10.0)
        assert result.returncode in {0, 1}, result.stderr
        payload = parse_json(result)
        last_payload = payload
        if payload["status"] == expected:
            return payload
        time.sleep(0.1)
    raise AssertionError(f"expected status {expected!r}, last payload was {last_payload!r}")


def fetch_health(port: int) -> dict:
    with request.urlopen(f"http://127.0.0.1:{port}{HEALTH_PATH}", timeout=2.0) as response:  # noqa: S310
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def test_start_status_restart_and_stop_after_crash(tmp_path: Path):
    runtime_root = tmp_path / "runtime-root"
    port = unused_port()

    try:
        start = run_cli(
            runtime_root,
            "start",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--format",
            "json",
            timeout=30.0,
        )
        assert start.returncode == 0, start.stderr or start.stdout
        started = parse_json(start)
        pid = started["pid"]
        assert started["status"] == "running"
        assert started["port"] == port
        assert started["restart_count"] == 0
        assert started["probe"]["status"] == "healthy"
        assert started["log_path"].startswith(".gsd/runtime/dev-server/logs/")
        health = fetch_health(port)
        assert is_valid_health_payload(health)
        assert health["service"] == "sentinelx"

        os.kill(pid, signal.SIGKILL)
        crashed = wait_for_status(runtime_root, "crashed")
        assert crashed["pid"] == pid
        assert crashed["port"] == port
        assert crashed["probe"]["status"] in {"refused", "timeout"}
        assert "no longer running" in crashed["last_failure_reason"]
        assert "provider_key" not in json.dumps(crashed)

        restart = run_cli(runtime_root, "restart", "--format", "json", timeout=30.0)
        assert restart.returncode == 0, restart.stderr or restart.stdout
        restarted = parse_json(restart)
        assert restarted["status"] == "running"
        assert restarted["port"] == port
        assert restarted["restart_count"] == 1
        assert restarted["probe"]["status"] == "healthy"
        health = fetch_health(port)
        assert is_valid_health_payload(health)
        assert health["service"] == "sentinelx"

        stopped_result = run_cli(runtime_root, "stop", "--format", "json", timeout=30.0)
        assert stopped_result.returncode == 0, stopped_result.stderr or stopped_result.stdout
        stopped = parse_json(stopped_result)
        assert stopped["status"] == "stopped"
        assert stopped["pid"] is None
        assert stopped["port"] == port
        assert stopped["restart_count"] == 1
        assert stopped["probe"]["status"] in {"refused", "timeout"}
    finally:
        cleanup = run_cli(runtime_root, "stop", "--format", "json", timeout=30.0)
        assert cleanup.returncode in {0, 1}
