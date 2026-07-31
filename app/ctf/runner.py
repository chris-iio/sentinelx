"""Allowlisted recon/enumeration command runner for CTF challenges.

SECURITY MODEL (deliberate SEC-13 exception, loopback-only surfaces):
- Never any shell invocation; argv lists only, built from preset profiles.
- Analysts pick a preset profile, never raw command lines. Every argument
  comes from the fixed profile templates below plus a validated target and
  an optional validated wordlist path.
- Targets must be a bare hostname/IPv4 or an http(s) URL; every character
  class is whitelisted so argument injection is impossible.
- Wordlists resolve to existing files under well-known system directories
  or ~/.sentinelx/wordlists; absolute paths from users are never accepted.
- Execution is bounded: per-profile timeout, streamed 64 KB output cap,
  minimal child environment, and process-group termination on timeout.
"""
from __future__ import annotations

import os
import re
import shutil
import signal
# Subprocess is required for the bounded allowlisted profiles described above.
import subprocess  # noqa: S404  # nosec B404
import threading
from pathlib import Path

from .flags import detect_flags

MAX_OUTPUT_CHARS = 64_000
_READ_CHUNK_BYTES = 8_192
_TERMINATION_GRACE_S = 0.25
_MINIMAL_ENV = {"PATH": os.defpath, "LANG": "C", "LC_ALL": "C"}

_HOST_RE = re.compile(
    r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*$"
)
_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_URL_RE = re.compile(
    r"^https?://(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*"
    r"(?::\d{1,5})?(?:/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*)?$"
)

_WORDLIST_DIRS = (
    Path("/usr/share/wordlists"),
    Path("/usr/share/seclists"),
    Path.home() / ".sentinelx" / "wordlists",
)

# Preset argv templates. {target} and {wordlist} placeholders are filled
# after validation; nothing else reaches the command line.
PROFILES: dict[str, dict] = {
    "nmap-quick": {
        "binary": "nmap",
        "argv": ["-sV", "-sC", "-Pn", "--top-ports", "1000", "{target}"],
        "target": "host",
        "needs_wordlist": False,
        "timeout_s": 300,
        "summary": "nmap -sV -sC top 1000 TCP ports",
    },
    "nmap-full-tcp": {
        "binary": "nmap",
        "argv": ["-sV", "-Pn", "-p-", "{target}"],
        "target": "host",
        "needs_wordlist": False,
        "timeout_s": 900,
        "summary": "nmap -sV all TCP ports",
    },
    "nmap-udp-top": {
        "binary": "nmap",
        "argv": ["-sU", "-Pn", "--top-ports", "100", "{target}"],
        "target": "host",
        "needs_wordlist": False,
        "timeout_s": 600,
        "summary": "nmap -sU top 100 UDP ports",
    },
    "gobuster-dir": {
        "binary": "gobuster",
        "argv": ["dir", "-u", "{target}", "-w", "{wordlist}", "-q", "--no-color"],
        "target": "url",
        "needs_wordlist": True,
        "timeout_s": 600,
        "summary": "gobuster directory bruteforce",
    },
    "gobuster-vhost": {
        "binary": "gobuster",
        "argv": ["vhost", "-u", "{target}", "-w", "{wordlist}", "-q", "--no-color"],
        "target": "url",
        "needs_wordlist": True,
        "timeout_s": 600,
        "summary": "gobuster vhost discovery",
    },
    "ffuf-dirs": {
        "binary": "ffuf",
        "argv": ["-u", "{target}", "-w", "{wordlist}", "-noninteractive"],
        "target": "url",
        "needs_wordlist": True,
        "timeout_s": 600,
        "summary": "ffuf content discovery (target must contain FUZZ)",
    },
    "nikto-default": {
        "binary": "nikto",
        "argv": ["-h", "{target}", "-nointeractive"],
        "target": "host_or_url",
        "needs_wordlist": False,
        "timeout_s": 900,
        "summary": "nikto web server scan",
    },
    "sqlmap-batch": {
        "binary": "sqlmap",
        "argv": ["-u", "{target}", "--batch", "--level=2", "--risk=2"],
        "target": "url",
        "needs_wordlist": False,
        "timeout_s": 900,
        "summary": "sqlmap automated injection probe",
    },
    "whatweb": {
        "binary": "whatweb",
        "argv": ["{target}"],
        "target": "url",
        "needs_wordlist": False,
        "timeout_s": 120,
        "summary": "whatweb fingerprinting",
    },
}

__all__ = ("MAX_OUTPUT_CHARS", "PROFILES", "RunResult", "run_profile")


class RunResult:
    """Outcome of one allowlisted tool execution."""

    def __init__(
        self,
        argv: list[str],
        exit_code: int,
        output: str,
        error: str = "",
        *,
        timed_out: bool = False,
        truncated: bool = False,
    ) -> None:
        self.argv = argv
        self.exit_code = exit_code
        self.output = output
        self.error = error
        self.timed_out = timed_out
        self.truncated = truncated
        self.flags = detect_flags(output)


def validate_target(target: str, kind: str) -> str:
    """Validate a target for the profile's target kind. Raises ValueError."""
    candidate = target.strip()
    if not candidate or len(candidate) > 253:
        raise ValueError("Target is required (max 253 chars).")
    host_ok = bool(_HOST_RE.match(candidate) or _IPV4_RE.match(candidate))
    url_ok = bool(_URL_RE.match(candidate))
    if kind == "host" and host_ok:
        return candidate
    if kind == "url" and url_ok:
        return candidate
    if kind == "host_or_url" and (host_ok or url_ok):
        return candidate
    expected = {"host": "hostname or IPv4", "url": "http(s) URL",
                "host_or_url": "hostname, IPv4, or http(s) URL"}[kind]
    raise ValueError(f"Invalid target — expected a {expected}.")


def resolve_wordlist(name: str) -> Path:
    """Resolve a wordlist by basename under the allowed directories."""
    basename = Path(name.strip()).name
    if not basename or basename.startswith("."):
        raise ValueError("Invalid wordlist name.")
    for directory in _WORDLIST_DIRS:
        candidate = directory / basename
        if candidate.is_file():
            return candidate
    matches = sorted(
        path
        for directory in _WORDLIST_DIRS
        if directory.is_dir()
        for path in directory.rglob(basename)
        if path.is_file()
    )
    if matches:
        return matches[0]
    raise ValueError(f"Wordlist not found: {basename}")


def available_profiles() -> dict[str, dict]:
    """Return profiles whose binary exists on PATH, annotated accordingly."""
    return {
        name: {**profile, "installed": shutil.which(profile["binary"]) is not None}
        for name, profile in PROFILES.items()
    }


def run_profile(
    profile_name: str,
    target: str,
    wordlist: str = "",
    *,
    timeout_override: int | None = None,
) -> RunResult:
    """Execute one preset profile against a validated target.

    Raises ValueError for invalid targets/wordlists or missing binaries.
    """
    profile = PROFILES.get(profile_name)
    if profile is None:
        raise ValueError(f"Unknown profile: {profile_name}")
    binary_path = shutil.which(profile["binary"])
    if binary_path is None:
        raise ValueError(f"Tool not installed: {profile['binary']}")

    resolved_target = validate_target(target, profile["target"])
    resolved_wordlist = ""
    if profile["needs_wordlist"]:
        resolved_wordlist = str(resolve_wordlist(wordlist))

    argv = [binary_path] + [
        arg.replace("{target}", resolved_target).replace("{wordlist}", resolved_wordlist)
        for arg in profile["argv"]
    ]
    timeout = timeout_override if timeout_override is not None else profile["timeout_s"]
    if timeout <= 0:
        raise ValueError("Timeout must be positive.")
    return _execute(argv, timeout)


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate the process session, then kill it if it does not exit."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        process.terminate()
    try:
        process.wait(timeout=_TERMINATION_GRACE_S)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()
    process.wait()


def _execute(argv: list[str], timeout_s: int) -> RunResult:
    """Run fixed argv while draining and bounding its combined output."""
    try:
        # argv comes from a fixed profile plus validated target and wordlist values.
        process = subprocess.Popen(  # noqa: S603  # nosec B603
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=_MINIMAL_ENV,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as exc:
        return RunResult(argv, exit_code=-1, output="", error=str(exc))

    output_stream = process.stdout
    if output_stream is None:
        _terminate_process_group(process)
        return RunResult(argv, exit_code=-1, output="", error="Output pipe unavailable")

    captured = bytearray()
    truncated = False

    def drain_output() -> None:
        nonlocal truncated
        while chunk := output_stream.read(_READ_CHUNK_BYTES):
            remaining = MAX_OUTPUT_CHARS - len(captured)
            if remaining > 0:
                captured.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated = True

    reader = threading.Thread(target=drain_output, name="ctf-output-drain", daemon=True)
    reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_group(process)
    reader.join(timeout=1)
    if reader.is_alive():
        output_stream.close()
        reader.join(timeout=1)

    output = captured.decode("utf-8", errors="replace")
    errors: list[str] = []
    if timed_out:
        errors.append(f"Timed out after {timeout_s}s")
    if truncated:
        errors.append(f"Output truncated at {MAX_OUTPUT_CHARS} bytes")
    return RunResult(
        argv,
        exit_code=-1 if timed_out else process.returncode,
        output=output,
        error="; ".join(errors),
        timed_out=timed_out,
        truncated=truncated,
    )
