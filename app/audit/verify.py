"""Isolated Foundry execution for model-generated proofs of concept.

Generated Solidity is untrusted code. The verifier copies only a bounded
Foundry source scope into a disposable directory and runs Forge in bubblewrap.
The sandbox has no network, parent home, or writable host path except the
copy. A pass verifies only the reported artifact hash. It does not validate a
broader finding.
"""
from __future__ import annotations

import hashlib
import os
import re
import selectors
import shutil
import signal
import stat
# Subprocess is required for the fixed bubblewrap isolation profile.
import subprocess  # noqa: S404  # nosec B404
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

__all__ = (
    "MAX_OUTPUT_BYTES",
    "MAX_POC_BYTES",
    "MAX_PROJECT_BYTES",
    "MAX_PROJECT_FILES",
    "verify_poc",
)

MAX_OUTPUT_BYTES = 64 * 1024
MAX_POC_BYTES = 256 * 1024
MAX_PROJECT_BYTES = 64 * 1024 * 1024
MAX_PROJECT_FILES = 5_000
MAX_PROJECT_FILE_BYTES = 8 * 1024 * 1024
MAX_TIMEOUT_SECONDS = 300

_PIPE_DRAIN_TIMEOUT_SECONDS = 0.25
_IO_POLL_SECONDS = 0.05
_REAP_TIMEOUT_SECONDS = 0.25

# These paths exist only inside the private bubblewrap tmpfs.
_SANDBOX_TMP = "/tmp"  # noqa: S108  # nosec B108
_SANDBOX_FOUNDRY_CACHE = f"{_SANDBOX_TMP}/foundry-cache"

_CONTRACT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
_COPY_FILES = ("foundry.toml", "foundry.lock", "remappings.txt")
_COPY_DIRECTORIES = ("src", "lib")
_SECRET_NAMES = {
    ".git",
    ".github",
    ".cache",
    "broadcast",
    "cache",
    "node_modules",
    "out",
}
_COMPILE_ERRORS = (
    "compiler run failed",
    "compilation failed",
    "failed to compile",
    "parsererror:",
    "typeerror:",
)


class _UnsafeProject(ValueError):
    """Raised when a project cannot be copied without unsafe behavior."""


@dataclass(frozen=True)
class _Execution:
    exit_code: int
    output: str
    output_sha256: str
    timed_out: bool
    truncated: bool
    error: str = ""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _result(
    status: str,
    reason: str,
    source_sha256: str,
    *,
    project_sha256: str = "",
    artifact_sha256: str = "",
    execution: _Execution | None = None,
) -> dict:
    execution = execution or _Execution(-1, "", _sha256(b""), False, False)
    return {
        "status": status,
        "reason": reason,
        "output": execution.output,
        "source_sha256": source_sha256,
        "project_sha256": project_sha256,
        "artifact_sha256": artifact_sha256,
        "output_sha256": execution.output_sha256,
        "timed_out": execution.timed_out,
        "truncated": execution.truncated,
    }


def _validate_inputs(
    project_root: Path, contract_name: str, poc_source: str, timeout: int
) -> tuple[Path, bytes]:
    if not isinstance(project_root, Path):
        raise ValueError("project_root must be a pathlib.Path")
    if project_root.is_symlink():
        raise ValueError("project_root must not be a symlink")
    try:
        root = project_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("project_root must be an existing directory") from exc
    if not root.is_dir():
        raise ValueError("project_root must be an existing directory")
    if not isinstance(contract_name, str) or not _CONTRACT_RE.fullmatch(contract_name):
        raise ValueError("contract_name must be a valid Solidity identifier (max 128 chars)")
    if not isinstance(poc_source, str):
        raise ValueError("poc_source must be text")
    if "\x00" in poc_source:
        raise ValueError("poc_source must not contain NUL characters")
    source = poc_source.encode("utf-8")
    if not source or len(source) > MAX_POC_BYTES:
        raise ValueError(f"poc_source must be 1 to {MAX_POC_BYTES} UTF-8 bytes")
    if not isinstance(timeout, int) or isinstance(timeout, bool):
        raise ValueError("timeout must be an integer")
    if timeout < 1 or timeout > MAX_TIMEOUT_SECONDS:
        raise ValueError(f"timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds")
    return root, source


def _is_secret_name(name: str) -> bool:
    lowered = name.lower()
    return lowered in _SECRET_NAMES or lowered == ".env" or lowered.startswith(".env.")


def _safe_relative(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if len(relative) > 1024 or any(part in ("", ".", "..") for part in relative.split("/")):
        raise _UnsafeProject("project contains an unsafe path")
    return relative


def _copy_regular_file(
    source: Path,
    destination: Path,
    root: Path,
    digest: "hashlib._Hash",
    counters: list[int],
) -> None:
    relative = _safe_relative(source, root)
    try:
        mode = source.lstat().st_mode
    except OSError as exc:
        raise _UnsafeProject(f"cannot inspect project entry: {relative}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise _UnsafeProject(f"project entry is not a regular file: {relative}")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(source, flags)
        with os.fdopen(descriptor, "rb") as stream:
            current_mode = os.fstat(stream.fileno()).st_mode
            if not stat.S_ISREG(current_mode):
                raise _UnsafeProject(f"project entry changed while copying: {relative}")
            data = stream.read(MAX_PROJECT_FILE_BYTES + 1)
    except OSError as exc:
        raise _UnsafeProject(f"cannot read project entry: {relative}") from exc

    if len(data) > MAX_PROJECT_FILE_BYTES:
        raise _UnsafeProject(f"project file exceeds {MAX_PROJECT_FILE_BYTES} bytes: {relative}")
    counters[0] += 1
    counters[1] += len(data)
    if counters[0] > MAX_PROJECT_FILES or counters[1] > MAX_PROJECT_BYTES:
        raise _UnsafeProject("project copy exceeds the file or byte limit")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    digest.update(relative.encode("utf-8"))
    digest.update(b"\0")
    digest.update(data)
    digest.update(b"\0")


def _copy_tree(
    source: Path,
    destination: Path,
    root: Path,
    digest: "hashlib._Hash",
    counters: list[int],
) -> None:
    try:
        entries = sorted(source.iterdir(), key=lambda entry: entry.name)
    except OSError as exc:
        relative = _safe_relative(source, root)
        raise _UnsafeProject(f"cannot inspect project directory: {relative}") from exc
    destination.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if _is_secret_name(entry.name) or entry.name.startswith("."):
            continue
        relative = _safe_relative(entry, root)
        try:
            mode = entry.lstat().st_mode
        except OSError as exc:
            raise _UnsafeProject(f"cannot inspect project entry: {relative}") from exc
        if stat.S_ISLNK(mode):
            raise _UnsafeProject(f"project symlinks are not allowed: {relative}")
        if stat.S_ISDIR(mode):
            _copy_tree(entry, destination / entry.name, root, digest, counters)
        elif stat.S_ISREG(mode):
            _copy_regular_file(entry, destination / entry.name, root, digest, counters)
        else:
            raise _UnsafeProject(f"special project entries are not allowed: {relative}")


def _copy_project(root: Path, destination: Path) -> str:
    config = root / "foundry.toml"
    if not config.exists():
        raise _UnsafeProject("not a Foundry project (no foundry.toml)")
    if config.is_symlink() or not config.is_file():
        raise _UnsafeProject("foundry.toml must be a regular file, not a symlink")

    digest = hashlib.sha256()
    counters = [0, 0]
    for name in _COPY_FILES:
        source = root / name
        if source.exists() or source.is_symlink():
            _copy_regular_file(source, destination / name, root, digest, counters)
    for name in _COPY_DIRECTORIES:
        source = root / name
        if not source.exists() and not source.is_symlink():
            continue
        try:
            mode = source.lstat().st_mode
        except OSError as exc:
            raise _UnsafeProject(f"cannot inspect project entry: {name}") from exc
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise _UnsafeProject(f"project source must be a regular directory: {name}")
        _copy_tree(source, destination / name, root, digest, counters)
    return digest.hexdigest()


def _runtime_binds() -> list[str]:
    argv: list[str] = []
    for path in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(path).exists():
            argv.extend(("--ro-bind", path, path))
    for path in ("/etc/ld.so.cache", "/etc/ld.so.conf"):
        if Path(path).is_file():
            argv.extend(("--ro-bind", path, path))
    return argv


def _bubblewrap_argv(bwrap: str, forge: str, worktree: Path, contract_name: str) -> tuple[str, ...]:
    return (
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--disable-userns",
        "--cap-drop",
        "ALL",
        "--clearenv",
        "--setenv",
        "HOME",
        "/home/sentinelx",
        "--setenv",
        "PATH",
        "/tool:/usr/bin:/bin",
        "--setenv",
        "FOUNDRY_FFI",
        "false",
        "--setenv",
        "FOUNDRY_CACHE_PATH",
        _SANDBOX_FOUNDRY_CACHE,
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        _SANDBOX_TMP,
        "--tmpfs",
        "/home",
        "--dir",
        "/home/sentinelx",
        "--dir",
        "/tool",
        "--ro-bind",
        forge,
        "/tool/forge",
        *_runtime_binds(),
        "--bind",
        str(worktree),
        "/work",
        "--chdir",
        "/work",
        "/tool/forge",
        "test",
        "--offline",
        "--match-contract",
        contract_name,
    )


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()


def _execute_sandbox(argv: tuple[str, ...], timeout: int) -> _Execution:
    try:
        # argv is the fixed bubblewrap profile built by _bubblewrap_argv.
        process = subprocess.Popen(  # noqa: S603  # nosec B603
            argv,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={},
            start_new_session=True,
        )
    except OSError as exc:
        return _Execution(-1, "", _sha256(b""), False, False, str(exc))

    if process.stdout is None:
        process.kill()
        process.wait()
        return _Execution(-1, "", _sha256(b""), False, False, "failed to capture output")

    captured = bytearray()
    output_digest = hashlib.sha256()
    truncated = False
    timed_out = False
    lingering_pipe = False
    group_killed = False
    deadline = time.monotonic() + timeout
    drain_deadline: float | None = None
    output_eof = False
    selector = selectors.DefaultSelector()
    try:
        output_fd = process.stdout.fileno()
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
            output_digest.update(chunk)
            remaining = MAX_OUTPUT_BYTES - len(captured)
            if remaining > 0:
                captured.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated = True
    finally:
        selector.close()
        process.stdout.close()

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
        errors.append(f"execution timed out after {timeout}s; process group killed")
    if lingering_pipe:
        errors.append("output pipe remained open; process group killed and output truncated")
    return _Execution(
        process.returncode if process.returncode is not None else -1,
        bytes(captured).decode("utf-8", errors="replace"),
        output_digest.hexdigest(),
        timed_out,
        truncated,
        "; ".join(errors),
    )


def verify_poc(
    project_root: Path,
    contract_name: str,
    poc_source: str,
    *,
    timeout: int = 120,
) -> dict:
    """Run one untrusted PoC in fail-closed OS isolation.

    ``verified`` means that Forge passed for the returned artifact hash.
    ``unproven`` means that the test ran and failed. Harness, compilation,
    isolation, timeout, and input failures are ``unverified``.
    """
    source_sha256 = ""
    try:
        root, source = _validate_inputs(project_root, contract_name, poc_source, timeout)
        source_sha256 = _sha256(source)
    except ValueError as exc:
        return _result("unverified", str(exc), source_sha256)

    bwrap = shutil.which("bwrap")
    if bwrap is None:
        return _result(
            "unverified",
            "bubblewrap is unavailable; isolation is required",
            source_sha256,
        )
    forge = shutil.which("forge")
    if forge is None:
        return _result("unverified", "forge is unavailable", source_sha256)
    try:
        bwrap_path = str(Path(bwrap).resolve(strict=True))
        forge_path = str(Path(forge).resolve(strict=True))
    except OSError:
        return _result("unverified", "bubblewrap or forge cannot be resolved", source_sha256)
    if not Path(bwrap_path).is_file() or not os.access(bwrap_path, os.X_OK):
        return _result("unverified", "bubblewrap is not an executable file", source_sha256)
    if not Path(forge_path).is_file() or not os.access(forge_path, os.X_OK):
        return _result("unverified", "forge is not an executable file", source_sha256)

    with tempfile.TemporaryDirectory(prefix="sentinelx-poc-") as temporary:
        worktree = Path(temporary) / "project"
        worktree.mkdir(mode=0o700)
        try:
            project_sha256 = _copy_project(root, worktree)
        except _UnsafeProject as exc:
            return _result("unverified", str(exc), source_sha256)

        test_directory = worktree / "test"
        test_directory.mkdir(mode=0o700)
        (test_directory / f"{contract_name}.t.sol").write_bytes(source)
        artifact_sha256 = _sha256(
            f"{project_sha256}:{contract_name}:{source_sha256}".encode("ascii")
        )
        argv = _bubblewrap_argv(bwrap_path, forge_path, worktree, contract_name)
        execution = _execute_sandbox(argv, timeout)

    if execution.timed_out:
        return _result(
            "unverified",
            execution.error,
            source_sha256,
            project_sha256=project_sha256,
            artifact_sha256=artifact_sha256,
            execution=execution,
        )
    if execution.error:
        return _result(
            "unverified",
            f"isolated execution was incomplete: {execution.error}",
            source_sha256,
            project_sha256=project_sha256,
            artifact_sha256=artifact_sha256,
            execution=execution,
        )

    lowered_output = execution.output.lower()
    if execution.exit_code == 0:
        status = "verified"
        reason = "exploit test passed for the exact reported artifact"
    elif lowered_output.startswith("bwrap:") or "creating new namespace failed" in lowered_output:
        status = "unverified"
        reason = "bubblewrap could not establish isolation"
    elif any(marker in lowered_output for marker in _COMPILE_ERRORS):
        status = "unverified"
        reason = "generated PoC or copied project did not compile"
    else:
        status = "unproven"
        reason = "exploit test ran but did not pass"
    return _result(
        status,
        reason,
        source_sha256,
        project_sha256=project_sha256,
        artifact_sha256=artifact_sha256,
        execution=execution,
    )
