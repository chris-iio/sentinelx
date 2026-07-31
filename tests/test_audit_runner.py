"""Tests for the audit tool runner (allowlisted profiles, path confinement)."""

import os
import stat
import threading
import time
from pathlib import Path

import pytest

from app.audit import runner


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    """Confine workspace roots to tmp_path."""
    monkeypatch.setenv("AUDIT_WORKSPACE_ROOTS", str(tmp_path))
    return tmp_path


@pytest.fixture()
def fake_tool(tmp_path, monkeypatch):
    """Install a fake executable on PATH that echoes its argv as JSON-ish text."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)

    def _make(name: str, script: str = '#!/bin/sh\necho "ran:$@"\n') -> Path:
        path = bin_dir / name
        path.write_text(script)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return _make


def test_validate_path_target_accepts_within_root(workspace):
    target = workspace / "project"
    target.mkdir()
    assert runner.validate_path_target(str(target)) == target


def test_validate_path_target_rejects_outside_root(workspace, tmp_path):
    outside = Path("/etc/hostname")
    with pytest.raises(ValueError, match="outside"):
        runner.validate_path_target(str(outside))


def test_validate_path_target_rejects_missing(workspace):
    with pytest.raises(ValueError, match="does not exist"):
        runner.validate_path_target(str(workspace / "nope"))


def test_validate_path_target_rejects_traversal(workspace):
    with pytest.raises(ValueError):
        runner.validate_path_target(str(workspace / ".." / "etc"))


def test_workspace_roots_fail_closed_without_configuration(monkeypatch):
    monkeypatch.delenv("AUDIT_WORKSPACE_ROOTS", raising=False)
    assert runner.workspace_roots() == []
    with pytest.raises(ValueError, match="disabled"):
        runner.validate_path_target("/etc/hostname")
    with pytest.raises(ValueError, match="disabled"):
        runner.run_profile("solc-version")


def test_run_profile_executes_allowlisted_argv(workspace, fake_tool):
    fake_tool("strings")
    target = workspace / "firmware.bin"
    target.write_bytes(b"\x00" * 16)
    result = runner.run_profile("strings", target=str(target))
    assert result.exit_code == 0
    assert str(target) in result.output
    assert result.argv[0].endswith("strings")
    assert result.argv[1:] == ("-n", "8", str(target))
    assert result.profile == "strings"
    assert result.root == str(workspace)
    assert result.target == str(target)
    assert result.started_at.endswith("Z")
    assert result.ended_at.endswith("Z")
    assert result.timed_out is False
    assert result.truncated is False


def test_run_profile_rejects_unknown_profile_and_missing_binary(workspace):
    with pytest.raises(ValueError, match="Unknown profile"):
        runner.run_profile("does-not-exist")
    with pytest.raises(ValueError, match="not installed"):
        runner.run_profile("slither", target=str(workspace))


def test_npm_audit_uses_target_dir_as_cwd(workspace, fake_tool):
    fake_tool("npm", '#!/bin/sh\necho "cwd:$(pwd) args:$@"\n')
    project = workspace / "proj"
    project.mkdir()
    result = runner.run_profile("npm-audit", target=str(project))
    assert result.exit_code == 0
    assert f"cwd:{project}" in result.output
    assert "args:audit --json" in result.output


def test_cwd_profile_requires_directory(workspace, fake_tool):
    fake_tool("npm")
    target = workspace / "file.txt"
    target.write_text("x")
    with pytest.raises(ValueError, match="directory"):
        runner.run_profile("npm-audit", target=str(target))


def test_run_profile_timeout(workspace, fake_tool):
    fake_tool("strings", "#!/bin/sh\nsleep 5\n")
    target = workspace / "f.bin"
    target.write_bytes(b"x")
    result = runner.run_profile("strings", target=str(target), timeout_override=1)
    assert result.exit_code < 0
    assert result.timed_out is True
    assert "process group was killed" in result.error


def test_host_profile_validation_reused(workspace, fake_tool):
    fake_tool("nmap")
    with pytest.raises(ValueError, match="Invalid target"):
        runner.run_profile("nmap-quick", target="not a host!")
    result = runner.run_profile("nmap-quick", target="127.0.0.1")
    assert result.argv[-1] == "127.0.0.1"


def test_available_profiles_annotates_installed(workspace, fake_tool):
    fake_tool("strings")
    profiles = runner.available_profiles()
    assert profiles["strings"]["installed"] is True
    assert profiles["slither"]["installed"] is False


def test_combined_output_has_strict_byte_cap(workspace, fake_tool):
    fake_tool(
        "strings",
        "#!/bin/sh\nhead -c 40000 /dev/zero | tr '\\0' a\n"
        "head -c 40000 /dev/zero | tr '\\0' b >&2\n",
    )
    target = workspace / "f.bin"
    target.write_bytes(b"x")
    result = runner.run_profile("strings", target=str(target))
    assert len(result.output.encode("utf-8")) == runner.MAX_OUTPUT_BYTES
    assert result.truncated is True
    assert "Output truncated" in result.error


def test_child_gets_minimal_environment(workspace, fake_tool, monkeypatch):
    fake_tool("strings", "#!/bin/sh\nprintf 'home=%s secret=%s' \"${HOME-unset}\" \"${AUDIT_SECRET-unset}\"\n")
    target = workspace / "f.bin"
    target.write_bytes(b"x")
    monkeypatch.setenv("AUDIT_SECRET", target.name)
    result = runner.run_profile("strings", target=str(target))
    assert result.output == "home=unset secret=unset"


def test_child_path_is_fixed_after_tool_resolution(workspace, fake_tool, monkeypatch):
    tool = fake_tool("strings", "#!/bin/sh\nprintf '%s' \"$PATH\"\n")
    target = workspace / "f.bin"
    target.write_bytes(b"x")
    monkeypatch.setenv("PATH", str(tool.parent))

    result = runner.run_profile("strings", target=str(target))

    assert result.argv[0] == str(tool)
    assert result.output == "/usr/bin:/bin"


def test_lingering_descendant_pipe_is_bounded(workspace, fake_tool):
    fake_tool("strings", "#!/bin/sh\n(sleep 30) &\nprintf 'parent done'\n")
    target = workspace / "f.bin"
    target.write_bytes(b"x")

    result = runner.run_profile("strings", target=str(target), timeout_override=2)

    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.truncated is True
    assert result.output == "parent done"
    assert "Output pipe remained open" in result.error


def test_timeout_kills_child_process_group(workspace, fake_tool):
    marker = workspace / "child-survived"
    fake_tool(
        "strings",
        f"#!/bin/sh\n(sleep 2; touch '{marker}') &\nsleep 10\n",
    )
    target = workspace / "f.bin"
    target.write_bytes(b"x")
    result = runner.run_profile("strings", target=str(target), timeout_override=1)
    time.sleep(1.5)
    assert result.timed_out is True
    assert not marker.exists()


def test_run_profile_rejects_work_when_capacity_is_full(
    workspace, fake_tool, monkeypatch
):
    fake_tool("solc")
    monkeypatch.setattr(runner, "_RUN_SLOTS", threading.BoundedSemaphore(0))
    with pytest.raises(runner.RunCapacityError, match="busy"):
        runner.run_profile("solc-version")


def test_wordlist_must_be_a_file_in_audit_root(workspace, fake_tool):
    fake_tool("ffuf")
    wordlist = workspace / "words.txt"
    wordlist.write_text("admin\n")
    result = runner.run_profile(
        "ffuf-dirs", target="https://example.test/FUZZ", wordlist=str(wordlist)
    )
    assert str(wordlist) in result.argv
    with pytest.raises(ValueError, match="outside"):
        runner.run_profile(
            "ffuf-dirs", target="https://example.test/FUZZ", wordlist="/etc/hosts"
        )
