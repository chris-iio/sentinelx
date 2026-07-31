"""Tests for isolated Foundry PoC verification."""

import hashlib
import os
import subprocess

from app.audit import verify
from app.audit.verify import verify_poc


def _project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "foundry.toml").write_text("[profile.default]\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "Vault.sol").write_text("contract Vault {}\n", encoding="utf-8")
    return root


def _tools(tmp_path, monkeypatch):
    tool_dir = tmp_path / "tools"
    tool_dir.mkdir(exist_ok=True)
    tools = {}
    for name in ("bwrap", "forge"):
        path = tool_dir / name
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o700)
        tools[name] = str(path)
    monkeypatch.setattr(verify.shutil, "which", tools.get)
    return tools


def _execution(returncode=0, output="", *, timed_out=False, truncated=False, error=""):
    encoded = output.encode()
    return verify._Execution(
        returncode,
        output[: verify.MAX_OUTPUT_BYTES],
        hashlib.sha256(encoded).hexdigest(),
        timed_out,
        truncated,
        error,
    )


def test_not_a_foundry_project_is_unverified(tmp_path, monkeypatch):
    _tools(tmp_path, monkeypatch)
    root = tmp_path / "empty"
    root.mkdir()
    result = verify_poc(root, "XPoC", "contract XPoC { }")
    assert result["status"] == "unverified"
    assert "foundry.toml" in result["reason"]


def test_required_tools_fail_closed(tmp_path, monkeypatch):
    root = _project(tmp_path)
    monkeypatch.setattr(verify.shutil, "which", lambda name: None)
    result = verify_poc(root, "XPoC", "contract XPoC { }")
    assert result["status"] == "unverified"
    assert "bubblewrap" in result["reason"]

    monkeypatch.setattr(
        verify.shutil, "which", lambda name: "/usr/bin/bwrap" if name == "bwrap" else None
    )
    result = verify_poc(root, "XPoC", "contract XPoC { }")
    assert result["status"] == "unverified"
    assert "forge" in result["reason"]


def test_isolation_argv_and_disposable_copy(tmp_path, monkeypatch):
    root = _project(tmp_path)
    tools = _tools(tmp_path, monkeypatch)
    (root / ".env").write_text("TOKEN=host-secret", encoding="utf-8")
    (root / "test").mkdir()
    existing = root / "test" / "XPoC.t.sol"
    existing.write_text("user work", encoding="utf-8")
    captured = {}

    def execute(argv, timeout):
        captured["argv"] = argv
        captured["timeout"] = timeout
        bind_index = argv.index("--bind")
        copy = os.path.realpath(argv[bind_index + 1])
        captured["copy"] = copy
        assert copy != os.path.realpath(root)
        assert open(os.path.join(copy, "test", "XPoC.t.sol"), encoding="utf-8").read() == (
            "contract XPoC { }"
        )
        assert not os.path.exists(os.path.join(copy, ".env"))
        assert not os.path.exists(os.path.join(copy, "test", "Existing.t.sol"))
        return _execution(0, "[PASS]")

    monkeypatch.setattr(verify, "_execute_sandbox", execute)
    result = verify_poc(root, "XPoC", "contract XPoC { }", timeout=7)

    argv = captured["argv"]
    assert argv[0] == os.path.realpath(tools["bwrap"])
    assert "--unshare-all" in argv
    assert "--disable-userns" in argv
    assert "--clearenv" in argv
    assert "--cap-drop" in argv
    assert ("--ro-bind", os.path.realpath(tools["forge"]), "/tool/forge") == tuple(
        argv[argv.index(os.path.realpath(tools["forge"])) - 1 : argv.index(os.path.realpath(tools["forge"])) + 2]
    )
    assert argv[-5:] == ("/tool/forge", "test", "--offline", "--match-contract", "XPoC")
    assert "/home/sentinelx" in argv
    assert argv[argv.index("FOUNDRY_CACHE_PATH") + 1] == "/tmp/foundry-cache"  # noqa: S108
    tmpfs_index = argv.index("--tmpfs")
    assert argv[tmpfs_index + 1] == "/tmp"  # noqa: S108
    assert tmpfs_index < argv.index("/tool/forge")
    assert str(root) not in argv
    assert captured["timeout"] == 7
    assert result["status"] == "verified"
    assert result["artifact_sha256"]
    assert result["output_sha256"] == hashlib.sha256(b"[PASS]").hexdigest()
    assert existing.read_text(encoding="utf-8") == "user work"
    assert not os.path.exists(captured["copy"])


def test_failure_statuses_are_honest(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _tools(tmp_path, monkeypatch)

    monkeypatch.setattr(verify, "_execute_sandbox", lambda argv, timeout: _execution(1, "[FAIL]"))
    failed = verify_poc(root, "XPoC", "contract XPoC { }")
    assert failed["status"] == "unproven"

    monkeypatch.setattr(
        verify,
        "_execute_sandbox",
        lambda argv, timeout: _execution(1, "Compiler run failed: parsererror:"),
    )
    compile_error = verify_poc(root, "XPoC", "broken {{{")
    assert compile_error["status"] == "unverified"
    assert "compile" in compile_error["reason"]

    monkeypatch.setattr(
        verify, "_execute_sandbox", lambda argv, timeout: _execution(1, "bwrap: denied")
    )
    isolation_error = verify_poc(root, "XPoC", "contract XPoC { }")
    assert isolation_error["status"] == "unverified"
    assert "isolation" in isolation_error["reason"]

    monkeypatch.setattr(
        verify,
        "_execute_sandbox",
        lambda argv, timeout: _execution(
            0,
            "partial",
            truncated=True,
            error="output pipe remained open; output truncated",
        ),
    )
    incomplete = verify_poc(root, "XPoC", "contract XPoC { }")
    assert incomplete["status"] == "unverified"
    assert "output pipe remained open" in incomplete["reason"]


def test_contract_source_root_and_timeout_are_validated(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _tools(tmp_path, monkeypatch)
    invalid = (
        (root, "../X", "contract X {}", 1, "contract_name"),
        (root, "XPoC", b"not text", 1, "poc_source"),
        (str(root), "XPoC", "contract X {}", 1, "project_root"),
        (root, "XPoC", "contract X {}", 0, "timeout"),
    )
    for project_root, name, source, timeout, reason in invalid:
        result = verify_poc(project_root, name, source, timeout=timeout)
        assert result["status"] == "unverified"
        assert reason in result["reason"]

    monkeypatch.setattr(verify, "MAX_POC_BYTES", 4)
    oversized = verify_poc(root, "XPoC", "12345")
    assert oversized["status"] == "unverified"
    assert "UTF-8 bytes" in oversized["reason"]


def test_project_root_and_source_symlinks_are_rejected(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _tools(tmp_path, monkeypatch)
    linked_root = tmp_path / "linked-project"
    linked_root.symlink_to(root, target_is_directory=True)
    result = verify_poc(linked_root, "XPoC", "contract XPoC { }")
    assert result["status"] == "unverified"
    assert "symlink" in result["reason"]

    (root / "src" / "Leak.sol").symlink_to("/etc/passwd")
    result = verify_poc(root, "XPoC", "contract XPoC { }")
    assert result["status"] == "unverified"
    assert "symlink" in result["reason"]


def test_project_scope_limits_are_enforced(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _tools(tmp_path, monkeypatch)
    monkeypatch.setattr(verify, "MAX_PROJECT_FILES", 1)
    result = verify_poc(root, "XPoC", "contract XPoC { }")
    assert result["status"] == "unverified"
    assert "limit" in result["reason"]


def test_execute_sandbox_bounds_combined_streamed_output(monkeypatch):
    monkeypatch.setattr(verify, "MAX_OUTPUT_BYTES", 1024)
    data = b"x" * (verify.MAX_OUTPUT_BYTES + 33)
    read_fd, write_fd = os.pipe()
    os.write(write_fd, data)
    os.close(write_fd)

    class Process:
        pid = 100
        returncode = 0
        stdout = os.fdopen(read_fd, "rb", buffering=0)

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            self.returncode = -9

    captured = {}

    def popen(argv, **kwargs):
        captured.update(kwargs)
        return Process()

    monkeypatch.setattr(verify.subprocess, "Popen", popen)
    result = verify._execute_sandbox(("/usr/bin/bwrap",), 1)
    assert result.truncated is True
    assert len(result.output.encode()) == verify.MAX_OUTPUT_BYTES
    assert result.output_sha256 == hashlib.sha256(data).hexdigest()
    assert captured["stderr"] is subprocess.STDOUT
    assert captured["env"] == {}
    assert captured["start_new_session"] is True


def test_execute_sandbox_kills_group_and_bounds_retained_pipe(monkeypatch):
    killed = []
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"partial")

    class Process:
        pid = 321
        returncode = None
        stdout = os.fdopen(read_fd, "rb", buffering=0)

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired("bwrap", timeout)

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(verify.subprocess, "Popen", lambda *args, **kwargs: Process())
    monkeypatch.setattr(verify.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(verify, "_PIPE_DRAIN_TIMEOUT_SECONDS", 0)
    try:
        result = verify._execute_sandbox(("/usr/bin/bwrap",), 0)
    finally:
        os.close(write_fd)

    assert result.timed_out is True
    assert result.truncated is True
    assert "timed out" in result.error
    assert "output pipe remained open" in result.error
    assert killed == [(321, verify.signal.SIGKILL)]


def test_foundry_config_symlink_is_rejected(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    target = tmp_path / "config"
    target.write_text("[profile.default]\n", encoding="utf-8")
    (root / "foundry.toml").symlink_to(target)
    _tools(tmp_path, monkeypatch)
    result = verify_poc(root, "XPoC", "contract XPoC { }")
    assert result["status"] == "unverified"
    assert "symlink" in result["reason"]
