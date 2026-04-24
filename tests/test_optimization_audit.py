"""Tests for the M013 optimization audit runner."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path("tools/optimization_audit.py")


def run_audit(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_template_mode_writes_ranked_artifact(tmp_path):
    output_path = tmp_path / "audit.md"

    result = run_audit("--mode", "template", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    content = output_path.read_text(encoding="utf-8")
    assert "measurement when practical" in content
    assert "code-path reasoning" in content
    assert "### do now" in content
    assert "### do next" in content
    assert "### later" in content
    assert "### leave alone" in content
    assert "make verify-fast" in content
    assert "make verify-deep" in content
    assert "## Verified rerun checklist" in content
    assert "Deterministic mocked-online browser proof" in content
    assert "R008" in content
    assert "R040" in content


def test_baseline_mode_writes_ranked_findings_and_notes(tmp_path):
    output_path = tmp_path / "audit.md"

    result = run_audit("--mode", "baseline", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    content = output_path.read_text(encoding="utf-8")
    assert "## Baseline stance" in content
    assert "## Verified rerun checklist" in content
    assert "mocked-online browser seam still passes end-to-end" in content
    assert "## Per-seam baseline notes" in content
    assert "## Continuity guardrail coverage" in content
    assert "status-snapshot-scaling" in content
    assert "Make `/enrichment/status` cursor-native end-to-end" in content
    assert "Keep WAL-backed cache/history stores and persistent connections unchanged" in content
    assert "_Fill during the do now pass_" not in content


def test_capture_command_records_measurement_metadata(tmp_path):
    output_path = tmp_path / "audit.md"

    result = run_audit(
        "--mode",
        "baseline",
        "--output",
        str(output_path),
        "--capture-command",
        "smoke::python3 -c 'print(\"ok\")'",
    )

    assert result.returncode == 0, result.stderr
    content = output_path.read_text(encoding="utf-8")
    assert "| smoke |" in content
    assert "python3 -c" in content
    assert "| 0 |" in content
    assert "ok" in content
    assert "Measurement captures" in content
