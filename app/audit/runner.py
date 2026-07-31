"""Run fixed audit tool profiles within explicit workspace roots.

The runner does not invoke a shell. It resolves each executable before launch,
uses fixed argument templates, and accepts only validated targets. Audit tool
execution is disabled until ``AUDIT_WORKSPACE_ROOTS`` names at least one
existing directory. Path targets and wordlists must stay in those roots after
symlink resolution.

Each child gets a small explicit environment and a new process session. Output
from stdout and stderr shares a strict 64 KiB byte cap. The reader keeps
draining after the cap. On timeout, the runner kills the child process group.
"""
from __future__ import annotations

import os
import selectors
import shutil
import signal
# Subprocess is required for fixed local tool profiles with bounded execution.
import subprocess  # noqa: S404  # nosec B404
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.ctf.runner import validate_target

MAX_OUTPUT_BYTES = 64 * 1024
MAX_OUTPUT_CHARS = MAX_OUTPUT_BYTES  # Backward-compatible public name.
MAX_PARALLEL_RUNS = 2

_TRUSTED_EXECUTABLE_PATH = "/usr/bin:/bin"
_PIPE_DRAIN_TIMEOUT_SECONDS = 0.25
_IO_POLL_SECONDS = 0.05
_REAP_TIMEOUT_SECONDS = 0.25

PROFILES: dict[str, dict] = {
    "slither": {
        "binary": "slither",
        "argv": ["{target}", "--json", "-"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 300,
        "format": "slither-json",
        "summary": "slither static analysis (JSON detectors)",
    },
    "mythril": {
        "binary": "myth",
        "argv": ["analyze", "{target}", "-o", "json"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 600,
        "format": "mythril-json",
        "summary": "mythril symbolic execution (JSON issues)",
    },
    "aderyn": {
        "binary": "aderyn",
        "argv": ["{target}", "--stdout"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 300,
        "format": None,
        "summary": "aderyn rust-based solidity analyzer",
    },
    "semgrep": {
        "binary": "semgrep",
        "argv": ["scan", "--config", "auto", "--json", "{target}"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 600,
        "format": "semgrep-json",
        "summary": "semgrep multi-language SAST (JSON results)",
    },
    "osv-scanner": {
        "binary": "osv-scanner",
        "argv": ["scan", "--format", "json", "--recursive", "{target}"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 600,
        "format": "osv-json",
        "summary": "osv-scanner dependency vulnerability scan",
    },
    "npm-audit": {
        "binary": "npm",
        "argv": ["audit", "--json"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": "target",
        "timeout_s": 300,
        "format": "npm-audit-json",
        "summary": "npm audit (runs with project dir as cwd)",
    },
    "forge-test": {
        "binary": "forge",
        "argv": ["test", "-vvv"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": "target",
        "timeout_s": 900,
        "format": None,
        "summary": "forge test (runs with project dir as cwd)",
    },
    "solc-version": {
        "binary": "solc",
        "argv": ["--version"],
        "target": "none",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 30,
        "format": None,
        "summary": "solc version check",
    },
    "nmap-quick": {
        "binary": "nmap",
        "argv": ["-sV", "-sC", "-Pn", "--top-ports", "1000", "{target}"],
        "target": "host",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 300,
        "format": None,
        "summary": "nmap -sV -sC top 1000 TCP ports",
    },
    "nuclei": {
        "binary": "nuclei",
        "argv": ["-u", "{target}", "-silent", "-severity", "medium,high,critical"],
        "target": "url",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 900,
        "format": None,
        "summary": "nuclei template scan (medium+)",
    },
    "ffuf-dirs": {
        "binary": "ffuf",
        "argv": ["-u", "{target}", "-w", "{wordlist}", "-noninteractive"],
        "target": "url",
        "needs_wordlist": True,
        "cwd": None,
        "timeout_s": 600,
        "format": None,
        "summary": "ffuf content discovery (target must contain FUZZ)",
    },
    "sqlmap-batch": {
        "binary": "sqlmap",
        "argv": ["-u", "{target}", "--batch", "--level=2", "--risk=2"],
        "target": "url",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 900,
        "format": None,
        "summary": "sqlmap automated injection probe",
    },
    "exiftool": {
        "binary": "exiftool",
        "argv": ["{target}"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 60,
        "format": None,
        "summary": "exiftool metadata dump",
    },
    "binwalk": {
        "binary": "binwalk",
        "argv": ["{target}"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 120,
        "format": None,
        "summary": "binwalk firmware/binary signature scan",
    },
    "strings": {
        "binary": "strings",
        "argv": ["-n", "8", "{target}"],
        "target": "path",
        "needs_wordlist": False,
        "cwd": None,
        "timeout_s": 60,
        "format": None,
        "summary": "strings (min length 8)",
    },
}

__all__ = (
    "MAX_OUTPUT_BYTES",
    "MAX_OUTPUT_CHARS",
    "MAX_PARALLEL_RUNS",
    "PROFILES",
    "RunCapacityError",
    "RunResult",
    "available_profiles",
    "run_profile",
    "validate_path_target",
    "workspace_roots",
)

_RUN_SLOTS = threading.BoundedSemaphore(MAX_PARALLEL_RUNS)


class RunCapacityError(RuntimeError):
    """Raised when all audit tool execution slots are in use."""


@dataclass(frozen=True)
class RunResult:
    """Immutable provenance and output from one tool execution."""

    run_id: str
    profile: str
    argv: tuple[str, ...]
    root: str | None
    target: str
    started_at: str
    ended_at: str
    exit_code: int
    timed_out: bool
    truncated: bool
    output: str
    error: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def workspace_roots() -> list[Path]:
    """Return explicitly configured, resolved workspace directories."""
    raw = os.environ.get("AUDIT_WORKSPACE_ROOTS", "")
    if not raw.strip():
        return []
    roots = [Path(part.strip()).expanduser() for part in raw.split(os.pathsep) if part.strip()]
    return [root.resolve() for root in roots if root.is_dir()]


def _require_workspace_roots() -> list[Path]:
    roots = workspace_roots()
    if not roots:
        raise ValueError(
            "Audit tools are disabled until AUDIT_WORKSPACE_ROOTS names an existing directory."
        )
    return roots


def _path_in_roots(target: str, roots: list[Path], *, file_only: bool = False) -> tuple[Path, Path]:
    candidate = target.strip()
    if not candidate or len(candidate) > 1024:
        raise ValueError("Path target is required (max 1024 chars).")
    resolved = Path(candidate).expanduser().resolve()
    if not resolved.exists() or (file_only and not resolved.is_file()):
        label = "File" if file_only else "Path"
        raise ValueError(f"{label} does not exist: {resolved}")
    root = next(
        (root for root in roots if resolved == root or root in resolved.parents),
        None,
    )
    if root is None:
        raise ValueError("Path is outside the allowed workspace roots.")
    return resolved, root


def validate_path_target(target: str) -> Path:
    """Resolve a path target under an explicit workspace root."""
    resolved, _ = _path_in_roots(target, _require_workspace_roots())
    return resolved


def available_profiles() -> dict[str, dict]:
    """Return profiles with their current executable availability."""
    return {
        name: {**profile, "installed": shutil.which(profile["binary"]) is not None}
        for name, profile in PROFILES.items()
    }


def run_profile(
    profile_name: str,
    target: str = "",
    wordlist: str = "",
    *,
    timeout_override: int | None = None,
) -> RunResult:
    """Execute one fixed profile after root and target validation."""
    roots = _require_workspace_roots()
    profile = PROFILES.get(profile_name)
    if profile is None:
        raise ValueError(f"Unknown profile: {profile_name}")
    binary_path = shutil.which(profile["binary"])
    if binary_path is None:
        raise ValueError(f"Tool not installed: {profile['binary']}")

    kind = profile["target"]
    cwd: str | None = None
    provenance_root: Path | None = None
    resolved_target = ""
    if kind == "path":
        path, provenance_root = _path_in_roots(target, roots)
        resolved_target = str(path)
        if profile["cwd"] == "target":
            if not path.is_dir():
                raise ValueError(f"Profile requires a directory target: {profile_name}")
            cwd = resolved_target
    elif kind in ("host", "url", "host_or_url"):
        resolved_target = validate_target(target, kind)
    elif kind != "none":
        raise ValueError(f"Unsupported target kind: {kind}")

    resolved_wordlist = ""
    if profile["needs_wordlist"]:
        wordlist_path, wordlist_root = _path_in_roots(wordlist, roots, file_only=True)
        resolved_wordlist = str(wordlist_path)
        provenance_root = provenance_root or wordlist_root

    argv = (binary_path,) + tuple(
        arg.replace("{target}", resolved_target).replace("{wordlist}", resolved_wordlist)
        for arg in profile["argv"]
    )
    timeout = timeout_override if timeout_override is not None else profile["timeout_s"]
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("Timeout must be a positive integer.")
    if not _RUN_SLOTS.acquire(blocking=False):
        raise RunCapacityError("All audit tool execution slots are busy.")
    try:
        return _execute(
            profile_name,
            argv,
            timeout,
            cwd,
            str(provenance_root) if provenance_root else None,
            resolved_target,
        )
    finally:
        _RUN_SLOTS.release()


def _child_environment() -> dict[str, str]:
    """Return the small environment exposed to audit tool children."""
    return {
        "PATH": _TRUSTED_EXECUTABLE_PATH,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()


def _execute(
    profile: str,
    argv: tuple[str, ...],
    timeout_s: int,
    cwd: str | None,
    root: str | None,
    target: str,
) -> RunResult:
    run_id = uuid.uuid4().hex
    started_at = _now()
    try:
        # argv comes from a fixed profile plus validated targets and paths.
        process = subprocess.Popen(  # noqa: S603  # nosec B603
            argv,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            env=_child_environment(),
            start_new_session=True,
        )
    except OSError as exc:
        return RunResult(
            run_id, profile, argv, root, target, started_at, _now(), -1,
            False, False, "", str(exc),
        )

    captured = bytearray()
    truncated = False
    output_stream = process.stdout
    if output_stream is None:
        _kill_process_group(process)
        try:
            process.wait(timeout=_REAP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            pass
        return RunResult(
            run_id, profile, argv, root, target, started_at, _now(), -1,
            False, False, "", "Failed to capture child output.",
        )

    timed_out = False
    lingering_pipe = False
    group_killed = False
    deadline = time.monotonic() + timeout_s
    drain_deadline: float | None = None
    output_eof = False
    selector = selectors.DefaultSelector()
    try:
        output_fd = output_stream.fileno()
        os.set_blocking(output_fd, False)
        selector.register(output_fd, selectors.EVENT_READ)
        while True:
            now = time.monotonic()
            return_code = process.poll()
            if return_code is None and not timed_out and now >= deadline:
                timed_out = True
                group_killed = True
                _kill_process_group(process)
                drain_deadline = now + _PIPE_DRAIN_TIMEOUT_SECONDS
            elif return_code is not None and output_eof:
                break
            elif return_code is not None and drain_deadline is None:
                drain_deadline = now + _PIPE_DRAIN_TIMEOUT_SECONDS

            if drain_deadline is not None and now >= drain_deadline:
                lingering_pipe = not output_eof
                if lingering_pipe and not group_killed:
                    _kill_process_group(process)
                    group_killed = True
                break

            if output_eof:
                time.sleep(min(_IO_POLL_SECONDS, max(0.0, deadline - now)))
                continue

            next_deadline = drain_deadline if drain_deadline is not None else deadline
            wait = min(_IO_POLL_SECONDS, max(0.0, next_deadline - now))
            if not selector.select(wait):
                continue
            try:
                chunk = os.read(output_fd, 8192)
            except BlockingIOError:
                continue
            if not chunk:
                output_eof = True
                selector.unregister(output_fd)
                continue
            remaining = MAX_OUTPUT_BYTES - len(captured)
            if remaining > 0:
                captured.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated = True
    finally:
        selector.close()
        output_stream.close()

    if lingering_pipe:
        truncated = True
    if process.poll() is None:
        try:
            process.wait(timeout=_REAP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            if not group_killed:
                _kill_process_group(process)
            process.kill()
            try:
                process.wait(timeout=_REAP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                pass

    errors: list[str] = []
    if timed_out:
        errors.append(f"Timed out after {timeout_s}s; the process group was killed.")
    if lingering_pipe:
        errors.append(
            "Output pipe remained open; the process group was killed and output was truncated."
        )
    if truncated and not lingering_pipe:
        errors.append(f"Output truncated at {MAX_OUTPUT_BYTES} combined bytes.")
    error = " ".join(errors)
    return RunResult(
        run_id=run_id,
        profile=profile,
        argv=argv,
        root=root,
        target=target,
        started_at=started_at,
        ended_at=_now(),
        exit_code=process.returncode if process.returncode is not None else -1,
        timed_out=timed_out,
        truncated=truncated,
        output=bytes(captured).decode("utf-8", errors="replace"),
        error=error,
    )
