"""Tests for the M013 optimization audit runner."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path("tools/optimization_audit.py")


def load_audit_module():
    module_name = "optimization_audit_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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
    assert "runtime-provider-diagnostics" in content
    assert "provider mix CacheAlpha:2d/0e, RateLimitBeta:2d/1e" in content
    assert "cache-hit ratio 1/5 (20%)" in content
    assert "Keep the runtime/provider dispatch path unchanged until diagnostics show a materially cache-hit-heavy workload." in content
    assert "The runtime/provider seam is now an explicit keep-decision" in content
    assert "limit it to a cache-hit-heavy dispatch reduction before touching semaphores" not in content
    assert "Keep per-provider backoff/session semantics as explicit measured keep-decisions" in content
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


def test_runtime_provider_summary_rejects_missing_fields():
    audit = load_audit_module()

    with pytest.raises(ValueError, match="missing diagnostics fields"):
        audit.summarize_runtime_provider_diagnostics(
            {
                "dispatch_count": 1,
                "providers": {"CacheAlpha": {"dispatch_count": 1, "error_count": 0}},
            }
        )


def test_render_measurement_section_escapes_markdown_delimiters():
    audit = load_audit_module()

    section = audit.render_measurement_section(
        [
            audit.CommandCapture(
                label="runtime-provider-diagnostics",
                command="internal",
                exit_code=0,
                duration_ms=12,
                summary="alpha | beta",
            )
        ]
    )

    assert "alpha \\| beta" in section


def test_run_internal_capture_returns_readable_failure_summary():
    audit = load_audit_module()

    capture = audit.run_internal_capture(
        label="runtime-provider-diagnostics",
        command="internal synthetic capture",
        measure=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    assert capture.exit_code == 1
    assert capture.summary == "Internal measurement failed: RuntimeError: boom"
