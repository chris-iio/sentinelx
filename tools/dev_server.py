#!/usr/bin/env python3
"""Repo-native helper layer for SentinelX's local dev-server manager.

This module owns the initial contract for the supported local dev loop:
- repo-root discovery
- manager-owned `.gsd/runtime/dev-server/**` path resolution
- status-file serialization and validation
- secret-free probing of `GET /api/health`

It intentionally does not start or stop child processes yet. Later tasks will add
lifecycle commands on top of these helpers.
"""
from __future__ import annotations

import argparse
import json
import socket
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
HEALTH_PATH = "/api/health"
HEALTH_PAYLOAD = {
    "service": "sentinelx",
    "status": "ok",
    "ready": True,
}

VALID_MANAGER_STATUSES = {"stopped", "starting", "healthy", "stale", "crashed"}
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

        host = payload["host"]
        if not isinstance(host, str) or not host.strip():
            raise StatusContractError(
                "Status payload must include a non-empty 'host' string."
            )

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
        host=host,
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


def write_status(paths: DevServerPaths, status: DevServerStatus) -> Path:
    """Persist runtime metadata atomically inside the managed runtime subtree."""
    managed_destination = paths.ensure_managed(paths.status_path)
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

    return DevServerStatus.from_payload(payload)


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
    if not isinstance(host, str) or not host.strip():
        raise StatusContractError("Host must be a non-empty string.")
    if host not in ALLOWED_LOCAL_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_LOCAL_HOSTS))
        raise StatusContractError(
            f"Host must stay local to SentinelX's dev loop ({allowed})."
        )
    return f"http://{host}:{normalize_port(port)}{HEALTH_PATH}"


def probe_health(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    timeout: float = 0.5,
) -> HealthProbeResult:
    """Probe the fixed local health contract without leaking response contents.

    Outcome categories are intentionally coarse and operator-focused:
    - healthy: exact 200 JSON contract matched
    - refused: connection could not be established
    - timeout: request timed out
    - malformed: non-200, non-JSON, or contract-drift response
    """
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


def render_status_text(status: DevServerStatus, paths: DevServerPaths) -> str:
    """Render a compact human-readable status view."""
    lines = [
        f"status: {status.status}",
        f"host: {status.host}",
        f"port: {status.port}",
        f"status_path: {paths.status_path.relative_to(paths.repo_root).as_posix()}",
    ]
    if status.probe is not None:
        lines.append(f"probe: {status.probe.status}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the supported helper surface."""
    parser = argparse.ArgumentParser(
        description=(
            "Inspect SentinelX's repo-native dev-server state contract and health-probe helpers."
        )
    )
    parser.add_argument(
        "--repo-root",
        help="Optional repo root override. Defaults to auto-discovery from this script.",
    )

    subparsers = parser.add_subparsers(dest="command")

    status_parser = subparsers.add_parser(
        "status",
        help="Print the current status contract without starting or stopping processes.",
    )
    status_parser.add_argument("--format", choices=("text", "json"), default="text")
    status_parser.add_argument("--host", default=DEFAULT_HOST)
    status_parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    paths = dev_server_paths(args.repo_root)

    if args.command == "status":
        status = read_status_or_default(paths, host=args.host, port=args.port)
        if args.format == "json":
            print(json.dumps(status.to_payload(), indent=2, sort_keys=True))
        else:
            print(render_status_text(status, paths))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
