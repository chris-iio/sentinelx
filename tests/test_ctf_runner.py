"""Unit tests for the allowlisted recon runner."""
import os
import sys

import pytest

from app.ctf import runner


def test_validate_target_host():
    assert runner.validate_target("10.10.11.42", "host") == "10.10.11.42"
    assert runner.validate_target("target.htb", "host") == "target.htb"


def test_validate_target_url():
    assert runner.validate_target("http://10.10.11.42:8080/api", "url")


def test_validate_target_rejects_injection():
    with pytest.raises(ValueError):
        runner.validate_target("10.10.11.42; rm -rf /", "host")
    with pytest.raises(ValueError):
        runner.validate_target("host --evil-flag", "host")
    with pytest.raises(ValueError):
        runner.validate_target("$(whoami)", "url")
    with pytest.raises(ValueError):
        runner.validate_target("", "host")


def test_validate_target_kind_mismatch():
    with pytest.raises(ValueError):
        runner.validate_target("http://example.htb", "host")
    with pytest.raises(ValueError):
        runner.validate_target("example.htb", "url")


def test_unknown_profile():
    with pytest.raises(ValueError):
        runner.run_profile("nmap;rm-rf", "10.10.11.42")


def test_missing_binary(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda binary: None)
    with pytest.raises(ValueError, match="not installed"):
        runner.run_profile("nmap-quick", "10.10.11.42")


def test_run_builds_expected_argv(monkeypatch, tmp_path):
    wordlist = tmp_path / "common.txt"
    wordlist.write_text("admin\nlogin\n")
    monkeypatch.setattr(runner, "_WORDLIST_DIRS", (tmp_path,))
    monkeypatch.setattr(runner.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    captured = {}

    def fake_execute(argv, timeout_s):
        captured["argv"] = argv
        captured["timeout_s"] = timeout_s
        return runner.RunResult(argv, 0, "80/tcp open http")

    monkeypatch.setattr(runner, "_execute", fake_execute)
    result = runner.run_profile("gobuster-dir", "http://target.htb", "common.txt")
    assert captured["argv"][0] == "/usr/bin/gobuster"
    assert captured["argv"][-2:] == ["-q", "--no-color"]
    assert str(wordlist) in captured["argv"]
    assert "http://target.htb" in captured["argv"]
    assert result.exit_code == 0


def test_wordlist_rejects_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "_WORDLIST_DIRS", (tmp_path,))
    with pytest.raises(ValueError):
        runner.resolve_wordlist("../../etc/passwd")
    with pytest.raises(ValueError):
        runner.resolve_wordlist(".hidden")


def test_wordlist_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "_WORDLIST_DIRS", (tmp_path,))
    with pytest.raises(ValueError, match="not found"):
        runner.resolve_wordlist("nope.txt")


def test_execute_streams_bounded_combined_output():
    script = (
        "import os; "
        f"os.write(1, b'A' * {runner.MAX_OUTPUT_CHARS}); "
        "os.write(2, b'overflow')"
    )

    result = runner._execute([sys.executable, "-c", script], 5)

    assert len(result.output.encode()) == runner.MAX_OUTPUT_CHARS
    assert result.exit_code == 0
    assert result.truncated is True
    assert "Output truncated" in result.error


def test_execute_timeout_preserves_partial_output_and_reports_state():
    script = "import sys,time; print('before timeout', flush=True); time.sleep(10)"

    result = runner._execute([sys.executable, "-c", script], 0.1)

    assert result.exit_code == -1
    assert result.output.strip() == "before timeout"
    assert result.timed_out is True
    assert "Timed out after 0.1s" in result.error


def test_execute_uses_minimal_environment_and_new_process_session(monkeypatch):
    real_popen = runner.subprocess.Popen
    captured = {}

    def recording_popen(*args, **kwargs):
        captured.update(kwargs)
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", recording_popen)
    result = runner._execute([sys.executable, "-c", "print('ok')"], 5)

    assert result.exit_code == 0
    assert captured["env"] == {"PATH": os.defpath, "LANG": "C", "LC_ALL": "C"}
    assert captured["start_new_session"] is True
    assert captured["stdin"] is runner.subprocess.DEVNULL


def test_run_result_detects_flags():
    result = runner.RunResult(["x"], 0, "found HTB{runner_flag} in output")
    assert result.flags == ["HTB{runner_flag}"]


def test_available_profiles_shape():
    profiles = runner.available_profiles()
    assert "nmap-quick" in profiles
    assert "installed" in profiles["nmap-quick"]
