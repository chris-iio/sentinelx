#!/usr/bin/env python3
"""Repo-native lifecycle manager for SentinelX's local dev server.

This module owns the checked-in implementation for the supported local development
workflow. Contributors should normally use the repo-native Make wrappers:
- make dev-server-start
- make dev-server-status
- make dev-server-restart
- make dev-server-stop

The direct CLI remains the single implementation source of truth:
- start
- status
- restart
- stop

Manager-owned runtime metadata stays under `.gsd/runtime/dev-server/**` and is
kept secret-free so operators can inspect child-process state without reading log
contents or leaking provider configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.health_contract import HEALTH_PATH, HEALTH_PAYLOAD

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
DEFAULT_STARTUP_TIMEOUT = 10.0
DEFAULT_SHUTDOWN_TIMEOUT = 5.0
DEFAULT_PROBE_TIMEOUT = 0.5
DEFAULT_PROBE_INTERVAL = 0.1
DEFAULT_STARTING_GRACE_SECONDS = 2.0

VALID_MANAGER_STATUSES = {"stopped", "starting", "running", "stale", "crashed"}
VALID_PROBE_STATUSES = {"healthy", "refused", "timeout", "malformed"}
ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class DevServerError(Exception):
    """Base error for dev-server helper failures."""


class RepoRootError(DevServerError):
    """Raised when the repository root cannot be discovered safely."""


class ManagedPathError(DevServerError):
    """Raised when a managed path escapes `.gsd/runtime/dev-server/**`."""


class StatusContractError(DevServerError):
    """Raised when the persisted status contract is missing or malformed."""


class StatusFileMissingError(StatusContractError):
    """Raised when the managed status file does not exist yet."""


@dataclass(frozen=True)
class DevServerPaths:
    """Manager-owned filesystem paths for the dev-server runtime state."""

    repo_root: Path
    runtime_dir: Path
    status_path: Path
    logs_dir: Path

    def ensure_managed(self, path: Path) -> Path:
        """Fail closed if a path escapes the managed runtime subtree."""
        resolved = path.resolve(strict=False)
        runtime_root = self.runtime_dir.resolve(strict=False)
        try:
            resolved.relative_to(runtime_root)
        except ValueError as exc:
            raise ManagedPathError(
                f"Managed path '{resolved}' escapes runtime root '{runtime_root}'."
            ) from exc
        return resolved


@dataclass(frozen=True)
class HealthProbeResult:
    """A bounded, secret-free outcome for the local health probe."""

    status: str
    checked_at: str
    url: str
    http_status: int | None = None
    detail: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "url": self.url,
            "http_status": self.http_status,
            "detail": self.detail,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "HealthProbeResult":
        allowed_keys = {"status", "checked_at", "url", "http_status", "detail"}
        unexpected_keys = set(payload) - allowed_keys
        if unexpected_keys:
            unexpected = ", ".join(sorted(unexpected_keys))
            raise StatusContractError(f"Probe payload has unexpected keys: {unexpected}.")

        required_keys = {"status", "checked_at", "url"}
        missing_keys = required_keys - set(payload)
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise StatusContractError(f"Probe payload is missing required keys: {missing}.")

        status = payload["status"]
        if status not in VALID_PROBE_STATUSES:
            raise StatusContractError(f"Unknown probe status '{status}'.")

        checked_at = payload["checked_at"]
        if not isinstance(checked_at, str) or not checked_at:
            raise StatusContractError("Probe payload must include a non-empty 'checked_at' string.")

        url = payload["url"]
        if not isinstance(url, str) or not url:
            raise StatusContractError("Probe payload must include a non-empty 'url' string.")

        http_status = payload.get("http_status")
        if http_status is not None and not isinstance(http_status, int):
            raise StatusContractError("Probe 'http_status' must be an integer when present.")

        detail = payload.get("detail")
        if detail is not None and not isinstance(detail, str):
            raise StatusContractError("Probe 'detail' must be a string when present.")

        return cls(
            status=status,
            checked_at=checked_at,
            url=url,
            http_status=http_status,
            detail=detail,
        )


@dataclass(frozen=True)
class DevServerStatus:
    """Persisted runtime metadata for the supported local dev loop."""

    status: str
    host: str
    port: int
    updated_at: str
    restart_count: int = 0
    pid: int | None = None
    log_path: str | None = None
    started_at: str | None = None
    last_failure_at: str | None = None
    last_failure_reason: str | None = None
    probe: HealthProbeResult | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "host": self.host,
            "port": self.port,
            "updated_at": self.updated_at,
            "restart_count": self.restart_count,
            "pid": self.pid,
            "log_path": self.log_path,
            "started_at": self.started_at,
            "last_failure_at": self.last_failure_at,
            "last_failure_reason": self.last_failure_reason,
            "probe": None if self.probe is None else self.probe.to_payload(),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DevServerStatus":
        allowed_keys = {
            "status",
            "host",
            "port",
            "updated_at",
            "restart_count",
            "pid",
            "log_path",
            "started_at",
            "last_failure_at",
            "last_failure_reason",
            "probe",
        }
        unexpected_keys = set(payload) - allowed_keys
        if unexpected_keys:
            unexpected = ", ".join(sorted(unexpected_keys))
            raise StatusContractError(f"Status payload has unexpected keys: {unexpected}.")

        required_keys = {"status", "host", "port", "updated_at", "restart_count", "probe"}
        missing_keys = required_keys - set(payload)
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise StatusContractError(f"Status payload is missing required keys: {missing}.")

        status = payload["status"]
        if status not in VALID_MANAGER_STATUSES:
            raise StatusContractError(f"Unknown dev-server status '{status}'.")

        host = normalize_host(payload["host"])
        port = normalize_port(payload["port"])

        updated_at = payload["updated_at"]
        if not isinstance(updated_at, str) or not updated_at:
            raise StatusContractError(
                "Status payload must include a non-empty 'updated_at' string."
            )

        restart_count = payload["restart_count"]
        if not isinstance(restart_count, int) or restart_count < 0:
            raise StatusContractError(
                "Status payload 'restart_count' must be a non-negative integer."
            )

        pid = payload.get("pid")
        if pid is not None and (not isinstance(pid, int) or pid <= 0):
            raise StatusContractError(
                "Status payload 'pid' must be a positive integer when present."
            )

        log_path = payload.get("log_path")
        if log_path is not None and not isinstance(log_path, str):
            raise StatusContractError(
                "Status payload 'log_path' must be a string when present."
            )

        started_at = payload.get("started_at")
        if started_at is not None and not isinstance(started_at, str):
            raise StatusContractError("Status payload 'started_at' must be a string when present.")

        last_failure_at = payload.get("last_failure_at")
        if last_failure_at is not None and not isinstance(last_failure_at, str):
            raise StatusContractError(
                "Status payload 'last_failure_at' must be a string when present."
            )

        last_failure_reason = payload.get("last_failure_reason")
        if last_failure_reason is not None and not isinstance(last_failure_reason, str):
            raise StatusContractError(
                "Status payload 'last_failure_reason' must be a string when present."
            )

        probe_payload = payload.get("probe")
        if probe_payload is None:
            probe = None
        elif isinstance(probe_payload, Mapping):
            probe = HealthProbeResult.from_payload(probe_payload)
        else:
            raise StatusContractError("Status payload 'probe' must be an object or null.")

        if status != "stopped":
            missing = []
            if pid is None:
                missing.append("pid")
            if log_path is None:
                missing.append("log_path")
            if started_at is None:
                missing.append("started_at")
            if missing:
                fields = ", ".join(missing)
                raise StatusContractError(
                    f"Status '{status}' requires launch metadata fields: {fields}."
                )

        return cls(
            status=status,
            host=host,
            port=port,
            updated_at=updated_at,
            restart_count=restart_count,
            pid=pid,
            log_path=log_path,
            started_at=started_at,
            last_failure_at=last_failure_at,
            last_failure_reason=last_failure_reason,
            probe=probe,
        )


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp without fractional seconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_now_slug() -> str:
    """Return a filesystem-safe UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")


def normalize_port(port: Any) -> int:
    """Validate and normalize a TCP port."""
    if isinstance(port, bool):
        raise StatusContractError("Port must be an integer between 1 and 65535.")

    try:
        value = int(port)
    except (TypeError, ValueError) as exc:
        raise StatusContractError("Port must be an integer between 1 and 65535.") from exc

    if value < 1 or value > 65535:
        raise StatusContractError("Port must be an integer between 1 and 65535.")

    return value


def normalize_host(host: Any) -> str:
    """Validate the host stays local to the operator machine."""
    if not isinstance(host, str) or not host.strip():
        raise StatusContractError("Host must be a non-empty string.")

    value = host.strip()
    if value not in ALLOWED_LOCAL_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_LOCAL_HOSTS))
        raise StatusContractError(
            f"Host must stay local to SentinelX's dev loop ({allowed})."
        )
    return value


def discover_repo_root(start: Path | None = None) -> Path:
    """Discover the repo root from this script or a caller-supplied path."""
    origin = (start or Path(__file__)).resolve()
    current = origin if origin.is_dir() else origin.parent

    for candidate in (current, *current.parents):
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "app").is_dir()
            and (candidate / "tools").is_dir()
        ):
            return candidate

    raise RepoRootError("Unable to discover the SentinelX repo root from the current path.")


def code_repo_root() -> Path:
    """Return the real source repo root that owns the Flask app code."""
    return discover_repo_root(Path(__file__))


def dev_server_paths(repo_root: Path | str | None = None) -> DevServerPaths:
    """Return the manager-owned runtime paths under `.gsd/runtime/dev-server/**`."""
    root = discover_repo_root() if repo_root is None else Path(repo_root).resolve()
    runtime_dir = root / ".gsd" / "runtime" / "dev-server"
    return DevServerPaths(
        repo_root=root,
        runtime_dir=runtime_dir,
        status_path=runtime_dir / "status.json",
        logs_dir=runtime_dir / "logs",
    )


def default_status(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> DevServerStatus:
    """Return the initial manager status when no runtime state exists yet."""
    return DevServerStatus(
        status="stopped",
        host=normalize_host(host),
        port=normalize_port(port),
        updated_at=utc_now(),
        restart_count=0,
        probe=None,
    )


def _atomic_write_text(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            temp_path = Path(handle.name)
        temp_path.replace(destination)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def managed_relative_path(paths: DevServerPaths, path: Path) -> str:
    """Return a repo-root-relative managed path string."""
    managed = paths.ensure_managed(path)
    return managed.relative_to(paths.repo_root).as_posix()


def resolve_managed_reference(paths: DevServerPaths, reference: str) -> Path:
    """Resolve a stored path reference and fail if it escapes the managed subtree."""
    candidate = Path(reference)
    resolved = candidate if candidate.is_absolute() else paths.repo_root / candidate
    return paths.ensure_managed(resolved)


def build_log_path(paths: DevServerPaths, host: str, port: int) -> tuple[Path, str]:
    """Allocate a manager-owned log path for a launch attempt."""
    filename = f"dev-server-{host.replace(':', '_')}-{port}-{utc_now_slug()}.log"
    absolute = paths.logs_dir / filename
    relative = managed_relative_path(paths, absolute)
    return absolute, relative


def write_status(paths: DevServerPaths, status: DevServerStatus) -> Path:
    """Persist runtime metadata atomically inside the managed runtime subtree."""
    managed_destination = paths.ensure_managed(paths.status_path)
    if status.log_path is not None:
        resolve_managed_reference(paths, status.log_path)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(status.to_payload(), indent=2, sort_keys=True) + "\n"
    _atomic_write_text(managed_destination, payload)
    return managed_destination


def load_status(paths: DevServerPaths) -> DevServerStatus:
    """Load and validate the persisted runtime metadata."""
    managed_source = paths.ensure_managed(paths.status_path)
    try:
        raw = managed_source.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StatusFileMissingError(
            f"Dev-server status file does not exist yet: {managed_source}"
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StatusContractError("Dev-server status file is malformed JSON.") from exc

    if not isinstance(payload, Mapping):
        raise StatusContractError("Dev-server status file must contain a JSON object.")

    status = DevServerStatus.from_payload(payload)
    if status.log_path is not None:
        resolve_managed_reference(paths, status.log_path)
    return status


def read_status_or_default(
    paths: DevServerPaths,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> DevServerStatus:
    """Return the saved status or a clean default when no status file exists yet."""
    try:
        return load_status(paths)
    except StatusFileMissingError:
        return default_status(host=host, port=port)


def build_health_url(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    """Build the local health URL after validating the caller-supplied host/port."""
    return f"http://{normalize_host(host)}:{normalize_port(port)}{HEALTH_PATH}"


def probe_health(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
) -> HealthProbeResult:
    """Probe the fixed local health contract without leaking response contents."""
    checked_at = utc_now()
    url = build_health_url(host, port)
    req = request.Request(url, headers={"Accept": "application/json"})  # noqa: S310

    try:
        with request.urlopen(req, timeout=timeout) as response:  # noqa: S310
            http_status = response.getcode()
            body = response.read()
    except error.HTTPError as exc:
        return HealthProbeResult(
            status="malformed",
            checked_at=checked_at,
            url=url,
            http_status=exc.code,
            detail=f"unexpected HTTP {exc.code}",
        )
    except error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
            return HealthProbeResult(
                status="timeout",
                checked_at=checked_at,
                url=url,
                detail="request timed out",
            )
        if isinstance(reason, ConnectionRefusedError) or (
            isinstance(reason, OSError) and getattr(reason, "errno", None) in {61, 111}
        ):
            return HealthProbeResult(
                status="refused",
                checked_at=checked_at,
                url=url,
                detail="connection refused",
            )
        return HealthProbeResult(
            status="refused",
            checked_at=checked_at,
            url=url,
            detail=str(reason or exc),
        )
    except (socket.timeout, TimeoutError):
        return HealthProbeResult(
            status="timeout",
            checked_at=checked_at,
            url=url,
            detail="request timed out",
        )

    if http_status != 200:
        return HealthProbeResult(
            status="malformed",
            checked_at=checked_at,
            url=url,
            http_status=http_status,
            detail=f"unexpected HTTP {http_status}",
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HealthProbeResult(
            status="malformed",
            checked_at=checked_at,
            url=url,
            http_status=http_status,
            detail="expected JSON health payload",
        )

    if payload != HEALTH_PAYLOAD:
        return HealthProbeResult(
            status="malformed",
            checked_at=checked_at,
            url=url,
            http_status=http_status,
            detail="unexpected health payload",
        )

    return HealthProbeResult(
        status="healthy",
        checked_at=checked_at,
        url=url,
        http_status=http_status,
    )


def process_is_running(pid: int | None) -> bool:
    """Return whether a process id is currently alive."""
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _started_recently(started_at: str | None, *, grace_seconds: float) -> bool:
    if not started_at:
        return False
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - started).total_seconds() < grace_seconds


def summarize_probe_failure(probe: HealthProbeResult | None) -> str:
    """Collapse probe state into a short operator-safe reason."""
    if probe is None:
        return "Health probe did not complete."
    if probe.status == "refused":
        return "Health probe refused connection."
    if probe.status == "timeout":
        return "Health probe timed out."
    if probe.status == "malformed":
        if probe.detail:
            return f"Health probe returned malformed response ({probe.detail})."
        return "Health probe returned malformed response."
    return "Health probe did not report healthy."


def status_output_payload(status: DevServerStatus, paths: DevServerPaths) -> dict[str, Any]:
    """Return the operator-facing status payload."""
    payload = status.to_payload()
    payload["status_path"] = paths.status_path.relative_to(paths.repo_root).as_posix()
    return payload


def render_status_text(status: DevServerStatus, paths: DevServerPaths) -> str:
    """Render a compact human-readable status view."""
    lines = [
        f"status: {status.status}",
        f"host: {status.host}",
        f"port: {status.port}",
        f"restart_count: {status.restart_count}",
        f"status_path: {paths.status_path.relative_to(paths.repo_root).as_posix()}",
    ]
    if status.pid is not None:
        lines.append(f"pid: {status.pid}")
    if status.log_path is not None:
        lines.append(f"log_path: {status.log_path}")
    if status.started_at is not None:
        lines.append(f"started_at: {status.started_at}")
    if status.last_failure_at is not None:
        lines.append(f"last_failure_at: {status.last_failure_at}")
    if status.last_failure_reason is not None:
        lines.append(f"last_failure_reason: {status.last_failure_reason}")
    if status.probe is not None:
        lines.append(f"probe: {status.probe.status}")
        if status.probe.detail:
            lines.append(f"probe_detail: {status.probe.detail}")
    return "\n".join(lines)


def emit_status(status: DevServerStatus, paths: DevServerPaths, output_format: str) -> None:
    """Print status in the requested format."""
    if output_format == "json":
        print(json.dumps(status_output_payload(status, paths), indent=2, sort_keys=True))
    else:
        print(render_status_text(status, paths))


def synthesize_contract_failure(
    paths: DevServerPaths,
    exc: Exception,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> DevServerStatus:
    """Build a visible failure payload when runtime metadata cannot be trusted."""
    safe_host = host if isinstance(host, str) and host in ALLOWED_LOCAL_HOSTS else DEFAULT_HOST
    try:
        safe_port = normalize_port(port)
    except StatusContractError:
        safe_port = DEFAULT_PORT

    return DevServerStatus(
        status="crashed",
        host=safe_host,
        port=safe_port,
        updated_at=utc_now(),
        restart_count=0,
        last_failure_at=utc_now(),
        last_failure_reason=str(exc),
        probe=None,
    )


def refresh_status(
    paths: DevServerPaths,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    probe_timeout: float = DEFAULT_PROBE_TIMEOUT,
    starting_grace_seconds: float = DEFAULT_STARTING_GRACE_SECONDS,
) -> DevServerStatus:
    """Combine stored metadata with a live health probe and persist the result."""
    status = read_status_or_default(paths, host=host, port=port)
    probe = probe_health(status.host, status.port, timeout=probe_timeout)
    now = utc_now()
    pid_running = process_is_running(status.pid)

    refreshed = replace(status, probe=probe, updated_at=now)

    if status.pid is None:
        refreshed = replace(refreshed, status="stopped")
        write_status(paths, refreshed)
        return refreshed

    if pid_running and probe.status == "healthy":
        refreshed = replace(refreshed, status="running")
        write_status(paths, refreshed)
        return refreshed

    if pid_running and _started_recently(status.started_at, grace_seconds=starting_grace_seconds):
        refreshed = replace(refreshed, status="starting")
        write_status(paths, refreshed)
        return refreshed

    if pid_running:
        refreshed = replace(
            refreshed,
            status="stale",
            last_failure_at=now,
            last_failure_reason=summarize_probe_failure(probe),
        )
        write_status(paths, refreshed)
        return refreshed

    probe_reason = summarize_probe_failure(probe)
    refreshed = replace(
        refreshed,
        status="crashed",
        last_failure_at=now,
        last_failure_reason=(
            f"Managed child pid {status.pid} is no longer running. {probe_reason}"
        ),
    )
    write_status(paths, refreshed)
    return refreshed


def _signal_managed_process(pid: int, sig: int) -> None:
    """Signal the manager-owned child process or its process group."""
    if hasattr(os, "killpg"):
        try:
            os.killpg(pid, sig)
            return
        except ProcessLookupError:
            raise
        except OSError:
            pass
    os.kill(pid, sig)


def stop_managed_process(pid: int, *, timeout: float = DEFAULT_SHUTDOWN_TIMEOUT) -> None:
    """Terminate a manager-owned child process, escalating if needed."""
    if not process_is_running(pid):
        return

    try:
        _signal_managed_process(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_is_running(pid):
            return
        time.sleep(0.05)

    try:
        _signal_managed_process(pid, signal.SIGKILL)
    except ProcessLookupError:
        return

    kill_deadline = time.monotonic() + min(timeout, 2.0)
    while time.monotonic() < kill_deadline:
        if not process_is_running(pid):
            return
        time.sleep(0.05)

    raise DevServerError(f"Managed child pid {pid} did not exit after SIGTERM/SIGKILL.")


def serve_child(host: str, port: int) -> int:
    """Run the Flask dev server inside the managed child process."""
    host = normalize_host(host)
    port = normalize_port(port)

    repo_root = code_repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from app import create_app

    app = create_app()
    app.run(host=host, port=port, debug=False, use_reloader=False)
    return 0


def _launch_child_process(paths: DevServerPaths, host: str, port: int, log_path: Path) -> subprocess.Popen[bytes]:
    """Spawn the managed dev-server child with stdout/stderr redirected to a log."""
    project_root = code_repo_root()
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "serve-child",
        "--host",
        host,
        "--port",
        str(port),
    ]

    with log_path.open("ab") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=str(project_root),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return process


def command_status(args: argparse.Namespace, paths: DevServerPaths) -> int:
    """Inspect the current state and live probe result."""
    host = normalize_host(args.host)
    port = normalize_port(args.port)
    try:
        status = refresh_status(
            paths,
            host=host,
            port=port,
            probe_timeout=args.probe_timeout,
            starting_grace_seconds=args.starting_grace_seconds,
        )
        exit_code = 0
    except StatusContractError as exc:
        status = synthesize_contract_failure(paths, exc, host=host, port=port)
        exit_code = 1

    emit_status(status, paths, args.format)
    return exit_code


def command_start(
    args: argparse.Namespace,
    paths: DevServerPaths,
    *,
    restart_count_base: int | None = None,
    emit_output: bool = True,
) -> int:
    """Start the managed dev server and wait for a healthy probe."""
    host = normalize_host(args.host)
    port = normalize_port(args.port)

    try:
        current = load_status(paths)
    except StatusFileMissingError:
        current = default_status(host=host, port=port)
    except StatusContractError as exc:
        status = synthesize_contract_failure(paths, exc, host=host, port=port)
        if emit_output:
            emit_status(status, paths, args.format)
        return 1

    if current.pid is not None and process_is_running(current.pid):
        status = refresh_status(
            paths,
            host=current.host,
            port=current.port,
            probe_timeout=args.probe_timeout,
            starting_grace_seconds=args.starting_grace_seconds,
        )
        if status.status in {"starting", "running", "stale"}:
            status = replace(
                status,
                last_failure_at=utc_now(),
                last_failure_reason=(
                    f"Managed child pid {status.pid} is already active; use restart instead."
                ),
            )
            write_status(paths, status)
            if emit_output:
                emit_status(status, paths, args.format)
            return 1

    restart_count = current.restart_count if restart_count_base is None else restart_count_base
    started_at = utc_now()
    log_absolute, log_relative = build_log_path(paths, host, port)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)

    process = _launch_child_process(paths, host, port, log_absolute)
    starting = DevServerStatus(
        status="starting",
        host=host,
        port=port,
        updated_at=started_at,
        restart_count=restart_count,
        pid=process.pid,
        log_path=log_relative,
        started_at=started_at,
        last_failure_at=current.last_failure_at,
        last_failure_reason=current.last_failure_reason,
        probe=None,
    )
    write_status(paths, starting)

    deadline = time.monotonic() + args.startup_timeout
    last_probe: HealthProbeResult | None = None
    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            failure = replace(
                starting,
                status="crashed",
                updated_at=utc_now(),
                last_failure_at=utc_now(),
                last_failure_reason=(
                    f"Managed child exited with code {exit_code} before reporting healthy."
                ),
                probe=last_probe,
            )
            write_status(paths, failure)
            if emit_output:
                emit_status(failure, paths, args.format)
            return 1

        last_probe = probe_health(host, port, timeout=args.probe_timeout)
        if last_probe.status == "healthy":
            running = replace(
                starting,
                status="running",
                updated_at=utc_now(),
                probe=last_probe,
            )
            write_status(paths, running)
            if emit_output:
                emit_status(running, paths, args.format)
            return 0
        time.sleep(args.probe_interval)

    try:
        stop_managed_process(process.pid, timeout=args.shutdown_timeout)
    except DevServerError:
        pass

    failure = replace(
        starting,
        status="crashed",
        updated_at=utc_now(),
        last_failure_at=utc_now(),
        last_failure_reason=(
            f"Managed child did not become healthy within {args.startup_timeout:.1f}s. "
            f"{summarize_probe_failure(last_probe)}"
        ),
        probe=last_probe,
    )
    write_status(paths, failure)
    if emit_output:
        emit_status(failure, paths, args.format)
    return 1


def command_stop(
    args: argparse.Namespace,
    paths: DevServerPaths,
    *,
    emit_output: bool = True,
) -> int:
    """Stop the manager-owned child if it is running."""
    try:
        current = load_status(paths)
    except StatusFileMissingError:
        current = default_status()
    except StatusContractError as exc:
        status = synthesize_contract_failure(paths, exc)
        if emit_output:
            emit_status(status, paths, args.format)
        return 1

    if current.pid is not None and process_is_running(current.pid):
        try:
            stop_managed_process(current.pid, timeout=args.shutdown_timeout)
        except DevServerError as exc:
            failed = replace(
                current,
                status="crashed",
                updated_at=utc_now(),
                last_failure_at=utc_now(),
                last_failure_reason=str(exc),
                probe=probe_health(current.host, current.port, timeout=args.probe_timeout),
            )
            write_status(paths, failed)
            if emit_output:
                emit_status(failed, paths, args.format)
            return 1

    probe = probe_health(current.host, current.port, timeout=args.probe_timeout)
    stopped = replace(
        current,
        status="stopped",
        pid=None,
        updated_at=utc_now(),
        probe=probe,
    )
    write_status(paths, stopped)
    if emit_output:
        emit_status(stopped, paths, args.format)
    return 0


def command_restart(args: argparse.Namespace, paths: DevServerPaths) -> int:
    """Restart the dev server using the recorded host/port configuration."""
    try:
        current = load_status(paths)
    except StatusFileMissingError:
        current = default_status()
    except StatusContractError as exc:
        status = synthesize_contract_failure(paths, exc)
        emit_status(status, paths, args.format)
        return 1

    host = current.host
    port = current.port
    restart_count = current.restart_count + 1

    stop_args = argparse.Namespace(
        format=args.format,
        shutdown_timeout=args.shutdown_timeout,
        probe_timeout=args.probe_timeout,
    )
    stop_exit = command_stop(stop_args, paths, emit_output=False)
    if stop_exit != 0:
        return stop_exit

    start_args = argparse.Namespace(
        host=host,
        port=port,
        format=args.format,
        startup_timeout=args.startup_timeout,
        shutdown_timeout=args.shutdown_timeout,
        probe_timeout=args.probe_timeout,
        probe_interval=args.probe_interval,
        starting_grace_seconds=args.starting_grace_seconds,
    )
    return command_start(start_args, paths, restart_count_base=restart_count, emit_output=True)


def add_common_output_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text")


def build_child_parser() -> argparse.ArgumentParser:
    """Build the hidden parser used only for the managed child process."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("serve-child")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    return parser


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the supported helper surface."""
    parser = argparse.ArgumentParser(
        description=(
            "Manage SentinelX's repo-native local dev-server lifecycle "
            "(wrapped by make dev-server-start|status|restart|stop)."
        )
    )
    parser.add_argument(
        "--repo-root",
        help="Optional runtime-root override for `.gsd/runtime/dev-server/**` state files.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="{start,status,restart,stop}")

    start_parser = subparsers.add_parser("start", help="Launch the managed local dev server.")
    add_common_output_format(start_parser)
    start_parser.add_argument("--host", default=DEFAULT_HOST)
    start_parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    start_parser.add_argument("--startup-timeout", type=float, default=DEFAULT_STARTUP_TIMEOUT)
    start_parser.add_argument("--shutdown-timeout", type=float, default=DEFAULT_SHUTDOWN_TIMEOUT)
    start_parser.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT)
    start_parser.add_argument("--probe-interval", type=float, default=DEFAULT_PROBE_INTERVAL)
    start_parser.add_argument(
        "--starting-grace-seconds",
        type=float,
        default=DEFAULT_STARTING_GRACE_SECONDS,
    )

    status_parser = subparsers.add_parser(
        "status",
        help="Print the current manager metadata combined with a live health probe.",
    )
    add_common_output_format(status_parser)
    status_parser.add_argument("--host", default=DEFAULT_HOST)
    status_parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    status_parser.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT)
    status_parser.add_argument(
        "--starting-grace-seconds",
        type=float,
        default=DEFAULT_STARTING_GRACE_SECONDS,
    )

    restart_parser = subparsers.add_parser(
        "restart",
        help="Restart the manager-owned child using the recorded host/port.",
    )
    add_common_output_format(restart_parser)
    restart_parser.add_argument("--startup-timeout", type=float, default=DEFAULT_STARTUP_TIMEOUT)
    restart_parser.add_argument("--shutdown-timeout", type=float, default=DEFAULT_SHUTDOWN_TIMEOUT)
    restart_parser.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT)
    restart_parser.add_argument("--probe-interval", type=float, default=DEFAULT_PROBE_INTERVAL)
    restart_parser.add_argument(
        "--starting-grace-seconds",
        type=float,
        default=DEFAULT_STARTING_GRACE_SECONDS,
    )

    stop_parser = subparsers.add_parser("stop", help="Stop the manager-owned child if present.")
    add_common_output_format(stop_parser)
    stop_parser.add_argument("--shutdown-timeout", type=float, default=DEFAULT_SHUTDOWN_TIMEOUT)
    stop_parser.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    if raw_argv and raw_argv[0] == "serve-child":
        child_args = build_child_parser().parse_args(raw_argv)
        return serve_child(child_args.host, child_args.port)

    parser = build_parser()
    args = parser.parse_args(raw_argv)
    if args.command is None:
        parser.print_help()
        return 0

    try:
        paths = dev_server_paths(args.repo_root)
        if args.command == "start":
            return command_start(args, paths)
        if args.command == "status":
            return command_status(args, paths)
        if args.command == "restart":
            return command_restart(args, paths)
        if args.command == "stop":
            return command_stop(args, paths)
    except DevServerError as exc:
        try:
            paths = dev_server_paths(getattr(args, "repo_root", None))
            status = synthesize_contract_failure(
                paths,
                exc,
                host=getattr(args, "host", DEFAULT_HOST),
                port=getattr(args, "port", DEFAULT_PORT),
            )
            emit_status(status, paths, getattr(args, "format", "text"))
        except DevServerError:
            print(f"dev-server error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
