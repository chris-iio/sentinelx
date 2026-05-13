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
    assert "Highest-confidence shipped fix" in content
    assert "request/status seam is now an explicit shipped keep-decision" in content
    assert "Keep `/enrichment/status` and `/api/status` on the orchestrator-owned incremental snapshot path" in content
    assert "Keep WAL-backed cache/history stores and persistent connections unchanged" in content
    assert "get_incremental_status(since=4990)" in content
    assert "Make `/enrichment/status` cursor-native end-to-end" not in content
    assert "Highest-confidence shipped frontend/render fix" in content
    assert "coordinator now caches stable per-IOC DOM handles and provider-count metadata" in content
    assert "Frontend work remains important, but it should now follow the shipped status-path fix" not in content
    assert "flush-wide `updateDashboardCounts()` recounts and `sortCardsBySeverity()` reorders" in content
    assert "If future frontend work is warranted, target flush-wide dashboard recounts and severity reorders instead of reopening the shipped coordinator-local handle cache." in content
    assert "The shipped coordinator-local cache retired repeated card/slot lookups" in content
    assert "Cache IOC card/slot handles inside the shared result-application coordinator before chasing deeper render changes." not in content
    assert "Shipped request/status delta path plus do-next flush-wide render follow-up" in content
    assert "_Fill during the do now pass_" not in content


def test_m017_baseline_uses_identity_grounded_contract(tmp_path):
    output_path = tmp_path / "m017-audit.md"

    result = run_audit(
        "--milestone-id",
        "M017",
        "--mode",
        "baseline",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    content = output_path.read_text(encoding="utf-8")
    assert "# M017 Optimization Audit — SentinelX" in content
    assert "## M017 identity-grounded contract" in content
    assert "docs/project-map.md" in content
    assert "local analyst IOC triage workbench" in content
    assert "D078" in content
    assert "D079" in content
    assert "D080" in content
    assert "R085" in content
    assert "R087" in content
    assert "S01 seam inventory priorities" in content
    assert "app/enrichment" in content
    assert "app/routes" in content
    assert "app/pipeline" in content
    assert "app/enrichment/orchestrator.py" in content
    assert "app/routes/_helpers.py" in content
    assert "app/pipeline/extractor.py" in content
    assert "S03 shipped proof" in content
    assert "S03 shipped the enrichment fan-out/status snapshot optimization" in content
    assert "S03 should target this path" not in content
    assert "### do now" in content
    assert "### do next" in content
    assert "### later" in content
    assert "### leave alone" in content
    assert "enrichment fan-out/status snapshot path" in content
    assert "status-snapshot-scaling" in content
    assert "measurement + code-path reasoning" in content
    assert "get_incremental_status(since=4990)" in content
    assert "tail rows plus aligned `cached_markers`" in content
    assert "without falling back to full result-list snapshots" in content
    assert "explicit code-path reasoning plus regression proof" in content
    assert "_Fill during the do now pass_" not in content
    assert "_Fill during the do next pass_" not in content
    assert "_Fill during the later pass_" not in content
    assert "_Fill during the leave alone pass_" not in content


def test_m017_baseline_notes_missing_project_map_without_silent_grounding(tmp_path):
    audit = load_audit_module()
    output_path = tmp_path / "m017-audit.md"
    document = audit.AuditDocument(
        milestone_id="M017",
        mode="baseline",
        repo_name="SentinelX",
        repo_root=tmp_path,
        output_path=output_path,
        generated_at="2026-01-01 00:00:00 UTC",
    )

    content = audit.render_document(document)

    assert "docs/project-map.md` was not found" in content
    assert "cannot truthfully claim full M017 identity grounding" in content


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


def test_failed_capture_command_is_recorded_without_aborting_generation(tmp_path):
    output_path = tmp_path / "audit.md"

    result = run_audit(
        "--milestone-id",
        "M017",
        "--mode",
        "baseline",
        "--output",
        str(output_path),
        "--capture-command",
        "bad::python3 -c 'import sys; print(\"bad capture\"); sys.exit(7)'",
    )

    assert result.returncode == 0, result.stderr
    content = output_path.read_text(encoding="utf-8")
    assert "| bad |" in content
    assert "| 7 |" in content
    assert "bad capture" in content
    assert "capture 'bad' failed with exit code 7" in result.stderr


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
