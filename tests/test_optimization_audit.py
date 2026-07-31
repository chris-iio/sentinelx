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


def test_capture_output_summary_keeps_bounded_tail_without_splitlines() -> None:
    audit = load_audit_module()

    class NoSplitLinesText(str):
        def splitlines(self, *_args, **_kwargs):
            raise AssertionError("capture summary should stream output lines")

    summary = audit.summarize_output(
        NoSplitLinesText("one\n two\nthree\n"),
        NoSplitLinesText("four\nfive\n"),
    )

    assert summary == "three | four | five"
    assert "splitlines" not in audit.summarize_output.__code__.co_names
    assert "deque" in audit.summarize_output.__code__.co_names


def test_cache_stats_measurement_counts_selects_without_listcomp() -> None:
    audit = load_audit_module()

    summary = audit.measure_cache_stats_query_count()

    assert "CacheStore.stats() executed 1 SELECT" in summary
    assert "total_entries=1" in summary
    assert "<listcomp>" not in {
        const.co_name
        for const in audit.measure_cache_stats_query_count.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_select_statement_detection_avoids_strip_and_upper_allocations() -> None:
    audit = load_audit_module()

    class NoStripUpperStatement(str):
        def lstrip(self, *_args, **_kwargs):
            raise AssertionError("SELECT detection should scan leading whitespace")

        def upper(self):
            raise AssertionError("SELECT detection should avoid uppercase allocation")

    assert audit._is_select_statement(NoStripUpperStatement(" \n\tselect 1")) is True
    assert audit._is_select_statement(NoStripUpperStatement("pragma table_info(cache)")) is False
    assert "lstrip" not in audit._is_select_statement.__code__.co_names
    assert "upper" not in audit._is_select_statement.__code__.co_names


def test_capture_spec_parser_avoids_split_and_strip_allocations() -> None:
    audit = load_audit_module()

    class NoSplitStripSpec(str):
        def split(self, *_args, **_kwargs):
            raise AssertionError("capture spec parsing should find the delimiter directly")

        def strip(self, *_args, **_kwargs):
            raise AssertionError("capture spec parsing should use shared index trimming")

    assert audit.parse_capture_spec(NoSplitStripSpec(" verify :: make verify-fast ")) == (
        "verify",
        "make verify-fast",
    )
    with pytest.raises(ValueError, match="Both LABEL and COMMAND"):
        audit.parse_capture_spec(NoSplitStripSpec("  :: make verify-fast "))
    assert "split" not in audit.parse_capture_spec.__code__.co_names
    assert "strip" not in audit.parse_capture_spec.__code__.co_names


def test_optimization_audit_records_use_slots_to_avoid_instance_dict(tmp_path: Path) -> None:
    audit = load_audit_module()
    lane = audit.VerificationLane("verify-fast", "make verify-fast", "default")
    guardrail = audit.Guardrail("R040", "Keep verification continuity.")
    seam = audit.Seam("runtime/provider", "continuity", ("prompt one", "prompt two"))
    capture = audit.CommandCapture("verify", "make verify-fast", 0, 1, "ok")
    finding = audit.BaselineFinding(
        "do now",
        "finding",
        "runtime/provider",
        "measurement",
        "evidence",
        "R040",
        "make verify-fast",
        "notes",
    )
    note = audit.SeamNote("runtime/provider", "boundary", "shape", "watch", "call")
    coverage = audit.GuardrailCoverage("R040", "runtime/provider", "proof", "notes")
    document = audit.AuditDocument(
        milestone_id="M013",
        mode="baseline",
        repo_name="SentinelX",
        repo_root=tmp_path,
        output_path=tmp_path / "audit.md",
        generated_at="2026-01-01 00:00:00 UTC",
    )

    assert not hasattr(lane, "__dict__")
    assert not hasattr(guardrail, "__dict__")
    assert not hasattr(seam, "__dict__")
    assert not hasattr(capture, "__dict__")
    assert not hasattr(finding, "__dict__")
    assert not hasattr(note, "__dict__")
    assert not hasattr(coverage, "__dict__")
    assert not hasattr(document, "__dict__")


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


def test_verify_fast_lane_documents_security_scanning() -> None:
    """Generated audit guidance should match the Makefile security-gated fast lane."""
    audit = load_audit_module()
    verify_fast_lane = next(
        lane for lane in audit.VERIFICATION_LANES if lane.name == "verify-fast"
    )

    assert verify_fast_lane.command == "make verify-fast"
    assert "security scanning" in verify_fast_lane.use_when
    assert "mocked-online browser behavior" in verify_fast_lane.use_when


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
    assert "_ordered_three_strings()" in content
    assert "_ordered_four_strings()" in content
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
    assert "app/routes/enrichment_jobs.py" in content
    assert "app/pipeline/extractor.py" in content
    assert "S03 shipped proof" in content
    assert "Current pipeline proof" in content
    assert "S03 shipped the enrichment fan-out/status snapshot optimization" in content
    assert "S03 should target this path" not in content
    assert "### do now" in content
    assert "### do next" in content
    assert "### later" in content
    assert "### leave alone" in content
    assert "enrichment fan-out/status snapshot path" in content
    assert "status-snapshot-scaling" in content
    assert "measurement + code-path reasoning" in content
    assert "app/enrichment/cache_payloads.py" in content
    assert "cache-hit hydration, marker keys, and cache-store payload shaping" in content
    assert "app/enrichment/attempt_execution.py::run_single_attempt()" in content
    assert "test_orchestrator_delegates_single_attempt_execution" in content
    assert "instead of retaining `_single_attempt()` as a compatibility delegator" in content
    assert "rebuilding single-attempt cache/adapter/latency flow in the orchestrator method body" in content
    assert "enrichment single-attempt cache/adapter/latency flow now lives in a dedicated attempt-execution helper" in content
    assert "get_incremental_status(since=4990)" in content
    assert "tail rows plus aligned `cached_markers`" in content
    assert "test_get_status_snapshot_copies_results_directly" in content
    assert "full-status result isolation" in content
    assert "test_get_incremental_status_nonnegative_since_does_not_slice_results" in content
    assert "test_get_incremental_status_copies_tail_without_list_constructor" in content
    assert "test_get_incremental_status_preserves_negative_since_behavior" in content
    assert "preserving Python negative-slice compatibility" in content
    assert "helper-owned tail append mutation" in content
    assert "append_result_tail_item" in content
    assert "aligned_cached_markers_snapshot()" in content
    assert "test_aligned_cached_markers_skips_iteration_for_short_tails" in content
    assert "constructor-copying cached markers or incremental result tails" in content
    assert "test_get_incremental_status_returns_empty_tail_beyond_retained_length" in content
    assert "test_get_incremental_status_builds_scalar_fields_without_items_scan" in content
    assert "Scalar status fields are now copied directly by known public key" in content
    assert "test_incremental_status_reuses_cache_marker_key_helper" in content
    assert "shared cache-marker key formatting" in content
    assert "itertools.islice()" in content
    assert "app/enrichment/status_snapshots.py" in content
    assert "app/enrichment/job_state.py" in content
    assert "app/enrichment/job_state.py::register_live_job()" in content
    assert "app/enrichment/job_state.py::resolved_job_record()" in content
    assert "live-versus-terminal record resolution" in content
    assert "app/enrichment/job_state.py::mark_live_job_failed()" in content
    assert "mark_live_job_complete()" in content
    assert "id-based terminal lifecycle mutation" in content
    assert "live job registration, stale terminal cleanup, and retention enforcement" in content
    assert "app/enrichment/job_state.py::record_live_lookup_result()" in content
    assert "id-based lookup result progress mutation" in content
    assert "initial job records, completion/failure mutation, live/terminal LRU eviction, eviction tombstones" in content
    assert "app/enrichment/job_state.py" in content
    assert "app/enrichment/job_state.py::evict_oldest_jobs()" in content
    assert "old orchestrator-local `_evict_if_needed()` wrapper is gone" in content
    assert "test_orchestrator_delegates_job_state_construction" in content
    assert "incremental status snapshots now return empty out-of-range cursor tails before walking retained results" in content
    assert "test_cached_markers_snapshot_copies_directly" in content
    assert "test_cached_markers_snapshot_short_paths_skip_fallback_loop" in content
    assert "cached_markers_snapshot()" in content
    assert "append_cached_marker_snapshot_entry()" in content
    assert "record_cached_marker()" in content
    assert "fallback marker-copy mutation delegates" in content
    assert "constructor-copying cached markers" in content
    assert "app/enrichment/diagnostics.py" in content
    assert "cache, retry, latency, and error counter mutation helpers" in content
    assert "app/enrichment/diagnostic_state.py::apply_job_diagnostics_update()" in content
    assert "test_orchestrator_delegates_diagnostic_update_helpers" in content
    assert "test_orchestrator_delegates_diagnostic_state_repair" in content
    assert "orchestrator-local diagnostics counter mutation closures" in content
    assert "rebuilding diagnostics state repair/provider bucket construction in the orchestrator method body" in content
    assert "enrichment diagnostics state repair and provider bucket selection now live in a diagnostic-state helper" in content
    assert "app/enrichment/dispatch_plan.py" in content
    assert "adapter/IOC dispatch-pair construction and keyed-provider semaphore construction" in content
    assert "append_supported_dispatch_pairs()" in content
    assert "direct empty/single/pair/three/four-IOC paths" in content
    assert "record_dispatch_pair()" in content
    assert "direct empty/single/pair/three/four-dispatch-pair paths" in content
    assert "passes dispatch-pair tuples through directly" in content
    assert "test_orchestrator_delegates_dispatch_setup_helpers" in content
    assert "embedding dispatch-pair/semaphore setup loops in the orchestrator class" in content
    assert "app/enrichment/job_execution.py::run_dispatch_pairs()" in content
    assert "submit_dispatch_pair()" in content
    assert "direct empty/single/pair/three/four-dispatch-pair submission paths" in content
    assert "test_orchestrator_delegates_thread_pool_dispatch_execution" in content
    assert "test_dispatch_execution_skips_pair_iteration_for_four_or_fewer_pairs" in content
    assert "embedding thread-pool dispatch mechanics in setup wiring or the orchestrator method body" in content
    assert "enrichment dispatch execution now delegates ThreadPoolExecutor/future plumbing" in content
    assert "through relative imports instead of round-tripping through the `app.enrichment` package facade" in content
    assert "test_top_level_enrichment_modules_use_relative_sibling_imports" in content
    assert "app/routes/enrichment_status.py" in content
    assert "json_results.py::apply_json_result()" in content
    assert "shared `status` field directly" in content
    assert "instead of retaining a private status-payload alias" in content
    assert "route-private job state, executor, setup, and polling helpers" in content
    assert "polling result serialization, status payload normalization, terminal payload shape" in content
    assert "live/terminal response selection" in content
    assert "enrichment_status.py::enrichment_status_response()" in content
    assert "enrichment_status.py::evicted_terminal_status()" in content
    assert "enrichment_status.py::unknown_terminal_status()" in content
    assert "enrichment_status.py::terminal_status_response()" in content
    assert "enrichment_status.py::live_status_response()" in content
    assert "enrichment_status.py::serialized_status_results()" in content
    assert "test_enrichment_status_owns_evicted_terminal_tombstone_shape" in content
    assert "test_enrichment_status_owns_unknown_terminal_tombstone_shape" in content
    assert "test_enrichment_status_terminal_response_owns_cursor_alignment" in content
    assert "test_enrichment_status_live_response_owns_result_serialization" in content
    assert "test_enrichment_status_route_delegates_response_decision" in content
    assert "route-owned live/terminal status branching" in content
    assert "app/routes/query_values.py::status_cursor_from_query()" in content
    assert "enrichment_jobs.py::_register_orchestrator()" in content
    assert "app/routes/enrichment_job_registry.py::register_orchestrator_state()" in content
    assert "enrichment_jobs.py::_build_enrichment_orchestrator()" in content
    assert "enrichment_jobs.py::_resolve_orchestrator_runtime_dependencies()" in content
    assert "explicit config-store factory" in content
    assert "enrichment_jobs.py::_submit_enrichment_job()" in content
    assert "test_setup_orchestrator_delegates_live_job_registration" in content
    assert "test_enrichment_jobs_public_exports_exclude_route_private_state" in content
    assert "test_route_job_registry_owns_live_orchestrator_retention" in content
    assert "test_setup_orchestrator_delegates_orchestrator_construction" in content
    assert "test_setup_orchestrator_accepts_explicit_runtime_dependencies" in content
    assert "test_setup_orchestrator_delegates_background_submission" in content
    assert "runtime dependency fallback isolated in `_resolve_orchestrator_runtime_dependencies()`" in content
    assert "rediscovering registry/cache/config-store dependencies during accepted Online setup" in content
    assert "mixing registry/cache current-app fallback resolution into setup lifecycle wiring" in content
    assert "OrderedDict mutation loops" in content
    assert "cache TTL lookup, configured-adapter selection" in content
    assert "executor submission and background task argument ordering" in content
    assert "status.get('cached_markers')` once per payload" in content
    assert "enrichment_status.py::append_serialized_result()" in content
    assert "test_enrichment_status_reads_cached_markers_once_per_payload" in content
    assert "short-result fast paths up to four entries stay direct" in content
    assert "test_serialize_results_shared_direct_accumulation" in content
    assert "test_append_serialized_result_owns_long_path_mutation" in content
    assert "test_serialize_results_delegates_long_path_append" in content
    assert "_get_enrichment_status()` against list-comprehension frames" in content
    assert "_build_status_payload()" in content
    assert "enrichment_status.py::build_status_payload()" in content
    assert "test_status_payload_uses_explicit_next_since_without_measuring_results" in content
    assert "eagerly measuring retained results when an explicit cursor exists" in content
    assert "_STATUS_NOT_FOUND_REASONS" in content
    assert "test_enrichment_status_not_found_reasons_use_static_membership_set" in content
    assert "terminal-not-found reason sets per response" in content
    assert "test_serialize_result_skips_empty_cached_marker_map" in content
    assert "test_serialize_result_reuses_cache_marker_key_helper" in content
    assert "enrichment_status.py::serialize_result()" in content
    assert "test_enrichment_jobs_delegates_status_payload_helpers" in content
    assert "test_enrichment_jobs_delegates_status_query_cursor" in content
    assert "enrichment_job_registry.py::registered_job_state()" in content
    assert "test_registered_job_state_reads_live_and_terminal_under_lock" in content
    assert "shared registry-state lookup" in content
    assert "no longer repeats `_orchestrators.get()`/`_terminal_jobs.get()`" in content
    assert "rebuilding polling payload helper bodies or route-owned live/terminal status branching" in content
    assert "repeating locked live/terminal registry lookups in route-facing accessors" in content
    assert "reading polling query args directly in the status route body" in content
    assert "duplicating unknown-job tombstone construction across status response branches" in content
    assert "mutating terminal polling cursors in the main response resolver branch" in content
    assert "serializing live polling results in the main response resolver branch" in content
    assert "reading cached-marker maps in the live response normalization helper" in content
    assert "test_save_serializes_results_and_iocs_with_direct_loops" in content
    assert "test_serialize_iocs_delegates_long_path_append" in content
    assert "ioc_payloads.py::_append_serialized_ioc()" in content
    assert "enrichment_history.py::save_enrichment_history()" in content
    assert "enrichment_history.py::save_enrichment_status_history()" in content
    assert "test_history_save_status_helper_delegates_serialization_helper" in content
    assert "test_run_enrichment_delegates_status_save_decision" in content
    assert "test_history_save_status_helper_records_skipped_without_persistence" in content
    assert "Background history-save serialization now accumulates result and IOC payloads with direct loops" in content
    assert "without retaining route-local history-save helper bodies" in content
    assert "retaining history-save persistence helper bodies in the job lifecycle route module" in content
    assert "app/enrichment/history_diagnostics.py" in content
    assert "without retaining a private mapping-copy alias" in content
    assert "route diagnostics module no longer owns the live history-save state" in content
    assert "without a route-local `_copy_mapping()` wrapper" in content
    assert "direct mapping-copy paths up to four keys" in content
    assert "test_history_save_diagnostics_falls_back_to_safe_defaults" in content
    assert "instead of `dict(...)` or route-module state wrappers" in content
    assert "test_history_save_diagnostics_presence_checks_avoid_timestamp_strip" in content
    assert "test_history_save_diagnostics_error_summary_strips_once" in content
    assert "test_orchestration_status_string_coercion_strips_once" in content
    assert "fixed history/status field groups and recordable outcome sets now live as owner-module constants" in content
    assert "constructor-copying history-save diagnostic defaults/snapshots" in content
    assert "keeping history-save diagnostic state in route modules" in content
    assert "retaining route-local mapping-copy wrappers" in content
    assert "repeatedly stripping diagnostic status strings" in content
    assert "rebuilding diagnostic/status field tuples" in content
    assert "test_orchestration_diagnostics_evicted_job_copies_terminal_snapshot_directly" in content
    assert "eviction_tombstone()" in content
    assert "route-level evicted tombstone construction delegates to `app/routes/enrichment_status.py::evicted_terminal_status()`" in content
    assert "rebuilding route-local evicted tombstone policy lambdas" in content
    assert "route-level live job registration delegates to `_register_orchestrator()`" in content
    assert "orchestrator construction delegates to `_build_enrichment_orchestrator()`" in content
    assert "background dispatch delegates to `_submit_enrichment_job()`" in content
    assert "rebuilding live job-state dictionaries in the dispatch path" in content
    assert "embedding thread-pool dispatch mechanics in setup wiring" in content
    assert "constructor-copying terminal tombstones" in content
    assert "test_get_diagnostics_falls_back_to_safe_defaults_for_malformed_state" in content
    assert "diagnostic provider items views" in content
    assert "skips per-result cache-key lookup work when the marker map is empty" in content
    assert "without falling back to full result-list snapshots" in content
    assert "explicit code-path reasoning plus regression proof" in content
    assert "Keep S04's shipped frontend/render optimization on the shared result-application severity-change gate." in content
    assert "duplicate broad `flush()` implementation" in content
    assert "only runs global dashboard recount/reorder calls when severity-affecting state changes" in content
    assert "provider-only/no-op deltas preserve summaries" in content
    assert "mocked-online browser checks for results and EmailRep continuity" in content
    assert "S04 is no longer an unresolved target" in content
    assert "Keep live polling progress updates on cached progress element handles." in content
    assert "app/static/src/ts/modules/enrichment.ts::init()" in content
    assert "document.getElementById" in content
    assert "live polling progress updates now reuse init-time progress element handles" in content
    assert "Keep summary-row expand toggles on cached details-panel lookups." in content
    assert "caches details panel lookups across repeated summary-row toggles" in content
    assert "Keep live warning banners on a cached warning element handle." in content
    assert "reuses the warning banner handle across repeated provider warnings" in content
    assert "`#enrich-warning`, `#enrich-progress`, `#export-btn`, and `#export-dropdown` once" in content
    assert "`initExportButton()` rendering" in content
    assert "`#export-btn` and `#export-dropdown` are each looked up once" in content
    assert "completion does not add another `export-btn` lookup" in content
    assert "Keep the shared result-application coordinator on cached per-IOC DOM handles before chasing broader flush-wide render work." in content
    assert "Map.values()` iterator" in content
    assert ".querySelector('.ioc-summary-row')" in content
    assert ".querySelector('.ioc-context-line')" in content
    assert ".querySelector('.verdict-label')" in content
    assert ".querySelector('.enrichment-details')" in content
    assert ".querySelector('.spinner-wrapper')" in content
    assert ".querySelector('.enrichment-waiting-text')" in content
    assert ".querySelector('.no-data-summary-row')" in content
    assert ".detail-link-footer" in content
    assert "do not repeat summary-row, context-line, verdict-label, spinner, or pending-indicator lookups" in content
    assert "skips reputation detail-row sorting while an IOC has only one reputation row" in content
    assert "reuses cached summary row and details handles when provided" in content
    assert "CTX-01: reuses a cached context line when provided" in content
    assert "finalization does not add another details-panel lookup" in content
    assert "finalization skips the old no-data summary guard query" in content
    assert "repeated finalization does not repeat `.detail-link-footer` lookup" in content
    assert "finalize walks cached IOC values without allocating a Map values iterator" in content
    assert "The shipped coordinator-local cache retired repeated card/summary-row/context-line/verdict-label/slot/details/spinner/pending-indicator/no-data-summary lookups" in content
    assert "Keep summary-row cached timestamp selection on a single-pass oldest lookup." in content
    assert "oldestCachedAt()" in content
    assert "`Array.prototype.sort` is patched to fail" in content
    assert "summary-row cached timestamp selection now uses a single-pass oldest lookup" in content
    assert "Keep inline context snippet formatting on direct string construction." in content
    assert "formatAsnContext()" in content
    assert "formatDnsAContext()" in content
    assert "CONTEXT_PROVIDERS" in content
    assert "readonly context-provider name list" in content
    assert "inline context snippet formatting now builds ASN and DNS text directly" in content
    assert "Keep no-data summary insertion on direct child scanning." in content
    assert "injectSectionHeadersAndNoDataSummary()" in content
    assert "no-data summary insertion now scans section children once" in content
    assert "querySelectorAll()` is patched to fail" in content
    assert "Keep summary attribution provider selection on a single-pass best-candidate scan." in content
    assert "computeAttribution()" in content
    assert "summary attribution now uses a single-pass best-candidate scan" in content
    assert "Keep summary worst-verdict computation on a single-pass scan." in content
    assert "computeWorstVerdict()" in content
    assert "summary worst-verdict computation now combines known-good override" in content
    assert "Keep exported worst-entry lookup on cached severity and malicious short-circuiting." in content
    assert "findWorstEntry()" in content
    assert "exported worst-entry lookup now caches severity" in content
    assert "Keep result-application severity detection on per-dirty IOC comparison." in content
    assert "whole-grid `.ioc-card` queries" in content
    assert "querySelectorAll` records no `.ioc-card` snapshot scan" in content
    assert "result-application severity detection now compares dirty IOC verdict changes during flush" in content
    assert "Keep provider-count metadata parsing cached by raw DOM value." in content
    assert "getProviderCounts()" in content
    assert "app/static/src/ts/types/ioc.test.ts" in content
    assert "repeated reads parse once" in content
    assert "severity ordering is guarded against array-map lookup construction" in content
    assert "provider-count metadata parsing now caches parsed DOM JSON by raw attribute value" in content
    assert "Keep provider detail-row sorting on cached severity keys." in content
    assert "sortDetailRows()" in content
    assert "exactly four `data-verdict` reads" in content
    assert "Array.from` is patched to fail" in content
    assert "provider detail-row sorting now caches row severity in an indexed NodeList pass" in content
    assert "Keep export dropdown actions on one delegated listener." in content
    assert "initExportButton()" in content
    assert "dropdown's `querySelectorAll()` is patched to fail" in content
    assert "export dropdown actions now use one delegated dropdown listener" in content
    assert "Keep IOC card sorting on cached severity keys." in content
    assert "sortCardsBySeverity()" in content
    assert "app/static/src/ts/modules/cards.test.ts" in content
    assert "card sorting still works when `Array.from` is patched to fail" in content
    assert "final append pass also uses an indexed loop" in content
    assert "IOC card sorting now caches card severity in an indexed NodeList pass" in content
    assert "Keep card verdict label updates on the shared classList helper." in content
    assert "applyCardVerdict()" in content
    assert "split().filter().join()" in content
    assert "card verdict label updates now share one classList-based helper" in content
    assert "Keep filter applications on cached static node lists." in content
    assert "app/static/src/ts/modules/filter.test.ts" in content
    assert "without additional `querySelectorAll` calls after init" in content
    assert "NodeList.prototype.forEach` patched to fail" in content
    assert "filter applications now reuse init-time static card/control node lists with indexed NodeList loops" in content
    assert "Keep card stagger initialization on indexed NodeList iteration." in content
    assert "initCardStagger()" in content
    assert "app/static/src/ts/modules/ui.test.ts" in content
    assert "NodeList.prototype.forEach` is patched to fail" in content
    assert "card stagger initialization now applies capped CSS indexes with indexed NodeList iteration" in content
    assert "Keep copy-button handling on one delegated listener." in content
    assert "app/static/src/ts/modules/clipboard.ts::init()" in content
    assert "app/static/src/ts/modules/clipboard.test.ts" in content
    assert "copy buttons now use one delegated document click handler" in content
    assert "Keep form initialization on shared element lookups." in content
    assert "app/static/src/ts/modules/form.ts::init()" in content
    assert "app/static/src/ts/modules/form.test.ts" in content
    assert "form initialization now reuses one element lookup bundle" in content
    assert "Keep settings accordion updates on cached header references." in content
    assert "initAccordion()" in content
    assert "app/static/src/ts/modules/settings.test.ts" in content
    assert "module source is guarded against `.forEach(` regressions" in content
    assert "settings accordion updates now reuse init-time header references with indexed loops" in content
    assert "Keep settings initialization on one section query." in content
    assert "app/static/src/ts/modules/settings.ts::init()" in content
    assert "no `.settings-section[data-provider]` query" in content
    assert "settings initialization now reuses one settings-section query with indexed NodeList loops" in content
    assert "Keep dashboard verdict-count updates on one count-element query." in content
    assert "updateDashboardCounts()" in content
    assert "no per-verdict `querySelector()` calls" in content
    assert "no `Array.prototype.includes()` membership scans" in content
    assert "NodeList.prototype.forEach` is patched to fail" in content
    assert "dashboard verdict-count updates now scan count elements once with indexed NodeList loops" in content
    assert "Keep frontend export text construction on direct string accumulation." in content
    assert "buildCSV()" in content
    assert "buildIocListText()" in content
    assert "copyAllIOCs()" in content
    assert "initExportButton()" in content
    assert "app/static/src/ts/modules/export.test.ts" in content
    assert "static CSV header is now a literal string" in content
    assert "guarded against `CSV_COLUMNS.join`" in content
    assert "duplicated copy-text append branches" in content
    assert "`Array.prototype.push` and `Array.prototype.join` are patched to fail" in content
    assert "guarded against `document.querySelectorAll()` scans" in content
    assert "module-load header joins" in content
    assert "copy-action card DOM scans" in content
    assert "frontend export text construction now accumulates CSV and copy-all IOC text directly" in content
    assert "frontend CSV exports now use a literal static header" in content
    assert "Keep IOC detail graph setup on single-pass node indexing." in content
    assert "renderRelationshipGraph()" in content
    assert "app/static/src/ts/modules/graph.test.ts" in content
    assert "Array.prototype.filter`, `Array.prototype.find`, `Array.prototype.map`, and `Array.prototype.forEach` are patched to fail" in content
    assert "empty graph-node/edge JSON parsing" in content
    assert "literal empty graph-edge payloads skip edge JSON parsing" in content
    assert "empty-edge graph payload makes `JSON.parse('[]')` fail" in content
    assert "IOC detail graph setup now splits nodes and indexes providers in single-pass loops" in content
    assert "Provider node drawing also uses indexed iteration" in content
    assert "Keep browser-route provider-count metadata on the direct count path." in content
    assert "provider_metadata.py::provider_counts_json()" in content
    assert "provider_metadata.py::provider_coverage()" in content
    assert "ProviderRegistry.registered_count()" in content
    assert "test_provider_counts_metadata_uses_direct_count_path" in content
    assert "test_provider_coverage_reuses_configured_provider_list" in content
    assert "test_analysis_route_delegates_provider_metadata_helpers" in content
    assert "stale compatibility aliases out of the route module" in content
    assert "test_registered_count_does_not_allocate_provider_list" in content
    assert "direct accumulator and `registry.provider_count_for_type()`" in content
    assert "registered-provider list copies for coverage counts" in content
    assert "dict-comprehension frame" in content
    assert "browser-route provider-count metadata and coverage counts now use registry direct count paths" in content
    assert "Keep Online fanout admission diagnostics on the direct count path." in content
    assert "_online_fanout_diagnostics()" in content
    assert "_online_admission()" in content
    assert "_log_online_limit_rejection()" in content
    assert "_resolve_online_limit_config()" in content
    assert "test_online_admission_centralizes_provider_and_limit_decision" in content
    assert "test_online_admission_short_circuits_when_no_providers" in content
    assert "test_online_limits_config_resolution_is_named_boundary" in content
    assert "route-supplied registry and limit inputs" in content
    assert "no longer reaches into `current_app.registry`" in content
    assert "route-supplied registry/config/limit forwarding" in content
    assert "pass `current_app.config` into `_online_limits_from_config()` explicitly" in content
    assert "parser-owned Flask config fallback resolution" in content
    assert "hidden Flask-global reads in the admission helper" in content
    assert "hidden route-level Flask config rediscovery for normal Online requests" in content
    assert "test_online_limit_rejection_logging_is_shared" in content
    assert "test_online_fanout_diagnostics_uses_direct_count_path" in content
    assert "secret-free Online limit warning format" in content
    assert "duplicated route-local admission-guard warning formatting" in content
    assert "analysis_workflow.py::start_online_analysis()" in content
    assert "test_browser_analyze_uses_shared_intake_workflow" in content
    assert "test_api_analyze_uses_shared_intake_workflow" in content
    assert "test_analyze_online_uses_shared_limit_config_helper" in content
    assert "test_online_uses_shared_limit_config_helper" in content
    assert "Online fanout admission diagnostics now use cached direct provider counts" in content
    assert "duplicated online-limit config parsing" in content
    assert "Keep browser-route enrichable progress totals on cached provider counts by IOC type." in content
    assert "provider_metadata.py::enrichable_count()" in content
    assert "test_enrichable_count_caches_provider_counts_by_ioc_type" in content
    assert "test_analyze_online_reuses_fanout_dispatch_count_for_progress_total" in content
    assert "browser-route enrichable progress totals now reuse admission fanout counts" in content
    assert "Keep online route configured-provider reads single-use across admission, coverage, and launch." in content
    assert "provider_metadata.py::provider_coverage()" in content
    assert "_setup_orchestrator()" in content
    assert "test_provider_coverage_reuses_configured_provider_list" in content
    assert "test_analyze_online_no_iocs_skips_enrichment_setup" in content
    assert "test_online_no_iocs_skips_enrichment_setup" in content
    assert "online routes now reuse the configured-provider list across admission" in content
    assert "skip provider setup entirely for zero-IOC submissions" in content
    assert "Keep API health registry detail on direct registry count paths." in content
    assert "api_health.py::registry_health_detail()" in content
    assert "api_health.py::build_api_health_checks()" in content
    assert "api_health.py::api_health_result()" in content
    assert "without a route-specific result or response-applier alias" in content
    assert "json_results.py::JsonResult" in content
    assert "ProviderRegistry.configured_count()" in content
    assert "test_health_touches_only_aggregate_provider_configuration" in content
    assert "test_api_health_route_delegates_dependency_probe_helpers" in content
    assert "test_api_health_result_owns_contract_payload_and_json_application" in content
    assert "api_health_route_response()" in content
    assert "explicit cache/history/registry/logger forwarding" in content
    assert "whole-app health helper inputs" in content
    assert "test_configured_count_does_not_allocate_provider_list" in content
    assert "registered or configured provider lists" in content
    assert "route-owned health payload construction" in content
    assert "route-owned health result construction" in content
    assert "duplicated health/analyze JSON result containers" in content
    assert "route-specific health result or response-applier aliases return" in content
    assert "route-owned health JSON response application" in content
    assert "API health registry detail now uses direct registered/configured count paths" in content
    assert "Keep health payload ordering and validation key sets precomputed." in content
    assert "HEALTH_CHECK_ORDER" in content
    assert "HEALTH_PAYLOAD_KEYS" in content
    assert "HEALTH_STATUSES" in content
    assert "literal tuple" in content
    assert "import-time sorted-list allocation" in content
    assert "test_health_contract_constants_stay_secret_free" in content
    assert "test_health_payload_uses_precomputed_check_order" in content
    assert "test_health_payload_validation_uses_precomputed_key_sets" in content
    assert "test_health_payload_uses_precomputed_status_set" in content
    assert "test_health_payload_detail_presence_skips_strip_allocation" in content
    assert "app/text_utils.py::has_non_whitespace()" in content
    assert "checks.values()` fail" in content
    assert "allowed-status set allocation" in content
    assert "values-view scans" in content
    assert "stripped-string allocation" in content
    assert "health payload construction and validation now reuse precomputed check order/key sets" in content
    assert "Keep shared contract frozensets on tuple inputs." in content
    assert "test_contract_static_frozensets_avoid_temporary_set_literals" in content
    assert "test_redaction_static_frozensets_avoid_temporary_set_literals" in content
    assert "shared health/diagnostic contract frozensets now use tuple inputs" in content
    assert "test_source_record_status_groups_are_static_frozensets" in content
    assert "test_archive_path_dot_segments_use_static_membership_set" in content
    assert "per-call diagnostic status/path membership checks" in content
    assert "Keep API analyze IOC serialization and grouping on one pass." in content
    assert "api_analyze()" in content
    assert "api_analysis.py::api_analyze_result()" in content
    assert "without a route-specific response-applier alias" in content
    assert "api_analyze_route_response()" in content
    assert "ioc_payloads.py::api_analysis_response_payload()" in content
    assert "_append_serialized_ioc_payload()" in content
    assert "API analyze error payload text" in content
    assert "test_groups_serialized_iocs_in_one_pass" in content
    assert "test_serialized_ioc_payload_append_owns_flat_and_grouped_mutation" in content
    assert "test_serialized_ioc_response_payload_delegates_mixed_group_append" in content
    assert "test_api_analysis_response_payload_owns_public_shape" in content
    assert "test_api_error_payloads_own_public_shape" in content
    assert "test_api_analyze_route_delegates_response_result_helper" in content
    assert "test_api_analyze_route_response_uses_shared_json_application" in content
    assert "route-specific result or response-applier aliases return" in content
    assert "test_online_no_providers_skips_ioc_serialization" in content
    assert "test_api_analyze_uses_shared_text_presence_check" in content
    assert "json_values.py::json_mapping_payload()" in content
    assert "analysis_workflow.py::build_analysis_intake()" in content
    assert "analysis_workflow.py::analysis_request_values()" in content
    assert "analysis_modes.py::DEFAULT_ANALYSIS_MODE" in content
    assert "public supported-mode label" in content
    assert "non-object JSON rejection" in content
    assert "route-local JSON body decoding" in content
    assert "route-local JSON field extraction" in content
    assert "route-owned API analyze response envelope construction" in content
    assert "route-owned API analyze validation/Online branching" in content
    assert "route-owned API analyze JSON decoding" in content
    assert "route-owned API analyze result construction" in content
    assert "route-owned API analyze JSON response application" in content
    assert "route-owned public API error text" in content
    assert "duplicated mode literals" in content
    assert "repeated mixed/long response serialize-and-group append mechanics" in content
    assert "API analyze responses now serialize and group each IOC in one pass only after online admission checks pass" in content
    assert "Keep browser analyze render decisions behind one result helper." in content
    assert "_ioc_template_context()" in content
    assert "analysis_results.py::browser_analyze_result()" in content
    assert "analysis_results.py::apply_browser_analyze_result()" in content
    assert "browser_analyze_route_response()" in content
    assert "browser_responses.py::apply_flash_redirect()" in content
    assert "analysis_results.py::online_result_template_extras()" in content
    assert "analysis_results.py::recent_analyses_context()" in content
    assert "analysis_results.py::index_page_result()" in content
    assert "index_page_route_response()" in content
    assert "shared `TemplateResult` response boundary" in content
    assert "test_analyze_groups_template_iocs_without_group_by_type" in content
    assert "test_analyze_online_without_api_key_skips_template_grouping" in content
    assert "test_browser_analyze_route_delegates_render_result_helper" in content
    assert "test_apply_browser_analyze_result_owns_flask_response_application" in content
    assert "test_apply_flash_redirect_owns_browser_flash_redirect_response_application" in content
    assert "test_online_result_template_extras_own_browser_shape" in content
    assert "test_recent_analyses_context_lives_in_result_helper" in content
    assert "old route wrapper out of the route module" in content
    assert "test_analyze_uses_shared_text_presence_check" in content
    assert "test_browser_analyze_uses_shared_intake_workflow" in content
    assert "browser analyze validation, Online branching, and render decisions now live in one result helper" in content
    assert "route-owned browser analyze validation/render branching" in content
    assert "route-owned browser analyze result construction" in content
    assert "route-owned browser analyze response application" in content
    assert "route-owned index result construction" in content
    assert "route-owned index response application" in content
    assert "duplicated browser flash/redirect plumbing" in content
    assert "route-owned Online result template-context construction" in content
    assert "route-local recent-history lookup/logging mechanics" in content
    assert "request text presence checks" in content
    assert "route-local form field extraction" in content
    assert "Keep history reload IOC reconstruction, grouping, and empty replay serialization lean." in content
    assert "history_replay.py::history_list_context()" in content
    assert "history_list_result()" in content
    assert "history_list_route_response()" in content
    assert "same `TemplateResult` response boundary" in content
    assert "history_replay.py::load_history_replay_context()" in content
    assert "history_replay.py::history_detail_result()" in content
    assert "history_detail_route_response()" in content
    assert "template_results.py::apply_template_result()" in content
    assert "history_replay.py::history_replay_context()" in content
    assert "_group_history_iocs()" in content
    assert "_append_history_ioc_row()" in content
    assert "test_history_groups_iocs_while_rebuilding_models" in content
    assert "test_history_ioc_row_append_owns_rebuild_and_group_mutation" in content
    assert "test_group_history_iocs_delegates_rebuild_group_append" in content
    assert "test_empty_history_skips_ioc_grouping" in content
    assert "empty history reloads skip the grouping helper entirely" in content
    assert "history_replay.py::history_results_json()" in content
    assert "no longer re-exports history replay JSON or IOC grouping helpers" in content
    assert "test_empty_history_results_skip_json_dumps" in content
    assert "test_history_route_delegates_replay_context_helpers" in content
    assert "test_template_result_helper_owns_abort_or_render_application" in content
    assert "test_history_list_delegates_template_context_helper" in content
    assert "route-local history list query limits" in content
    assert "shared empty provider-counts JSON literal" in content
    assert "ad hoc empty provider-count JSON literals" in content
    assert "route-owned history list/replay template shape" in content
    assert "route-owned history list/detail result construction" in content
    assert "route-owned history list/detail response application" in content
    assert "route-owned history detail render-or-404 branching" in content
    assert "route-owned history detail abort/render application" in content
    assert "route-local history record loading" in content
    assert "missing-record 404 behavior" in content
    assert "app/static/src/ts/modules/history.test.ts" in content
    assert "empty replay JSON parsing" in content
    assert "repeated persisted-row rebuild/group append mechanics" in content
    assert "`#enrich-progress`, `#enrich-progress-text`, `#export-btn`, and `#export-dropdown` once" in content
    assert "parsed replay verifies each history completion/export ID is looked up once" in content
    assert "repeated completion/export ID lookups on history reload" in content
    assert "history reload now rebuilds and groups persisted IOC models in one pass, skips empty-history grouping, and returns the empty replay JSON literal" in content
    assert "Keep IOC detail valid-type checks on a precomputed set." in content
    assert "detail_graph.py` now precomputes `VALID_IOC_TYPES`" in content
    assert "no longer retains compatibility aliases for detail graph helpers" in content
    assert "app/routes/detail_graph.py" in content
    assert "detail_graph.py::load_detail_template_context()" in content
    assert "detail_graph.py::detail_page_result()" in content
    assert "detail_page_route_response()" in content
    assert "detail_graph.py::detail_template_context()" in content
    assert "test_valid_ioc_types_are_precomputed" in content
    assert "test_detail_route_delegates_graph_payload_helpers" in content
    assert "test_detail_route_delegates_template_context_helper" in content
    assert "test_append_provider_graph_payload_owns_long_path_mutation" in content
    assert "test_graph_data_skips_iteration_for_empty_single_pair_three_or_four_results" in content
    assert "test_detail_page_empty_cache" in content
    assert "literal empty graph payloads" in content
    assert "repeated provider graph node/edge construction" in content
    assert "repeated graph append mutation" in content
    assert "route-owned graph helper bodies" in content
    assert "route-owned cache lookup/type rejection" in content
    assert "route-owned detail render-or-404 branching" in content
    assert "route-owned detail result construction" in content
    assert "route-owned detail response application" in content
    assert "route-owned detail abort/render application" in content
    assert "route-owned detail template shape" in content
    assert "discarded empty-cache graph node allocation" in content
    assert "valid-type generator/comprehension frames" in content
    assert "IOC detail routes now use a precomputed valid-type set" in content
    assert "Keep orchestration diagnostic export coercion on bounded iteration." in content
    assert "_coerce_orchestration_diagnostics_for_export()" in content
    assert "_set_export_child_scalar()" in content
    assert "itertools.islice()" in content
    assert "test_orchestration_diagnostics_export_coercion_uses_bounded_iteration" in content
    assert "test_orchestration_diagnostics_export_coercion_does_not_slice_lists" in content
    assert "orchestration diagnostic export coercion now applies top-level, nested dict, and list caps with bounded key/list iteration" in content
    assert "orchestration diagnostic export list coercion now accumulates primitive list values directly for up to four entries" in content
    assert "nested child scalar assignment delegates" in content
    assert "orchestration diagnostic mapping items-view allocation" in content
    assert "Keep diagnostic source sanitization on bounded mapping and sequence iteration." in content
    assert "app/diagnostics/runtime_payloads.py" in content
    assert "runtime_payloads.py` now calls `jsonish` owner helpers without re-exporting JSON-safe cap aliases" in content
    assert "sources.py` no longer imports unused JSON-safe cap aliases" in content
    assert "unused JSON-safe cap aliases in source descriptor and runtime payload factories" in content
    assert "runtime payload construction for config-secret inventory, cache stats, recent history, health, and orchestration diagnostics" in content
    assert "imports that sibling module directly instead of through the package facade or parallel symbol imports" in content
    assert "public default/type aliases assigned from the runtime payload owner" in content
    assert "runtime type aliases kept out of `sources.py::__all__`" in content
    assert "imports the runtime payload sibling directly rather than via the package facade or parallel symbol imports" in content
    assert "public default/type aliases still point at the runtime payload owner" in content
    assert "runtime type aliases are not wildcard-public source exports" in content
    assert "package-facade self-imports for internal runtime payload helpers" in content
    assert "parallel runtime-payload symbol imports in the source descriptor factory" in content
    assert "wildcard-public runtime type aliases from the source descriptor factory" in content
    assert "app/routes/diagnostic_export.py::diagnostic_export_response()" in content
    assert "app/routes/diagnostic_export.py::diagnostic_export_route_response()" in content
    assert "app/routes/diagnostic_export.py::diagnostic_export_failure_response()" in content
    assert "timestamp capture through an injectable clock" in content
    assert "ConfigStore construction through an explicit factory" in content
    assert "passes the cache/history stores explicitly" in content
    assert "helper no longer dereferences app stores" in content
    assert "whole-app diagnostic helper inputs" in content
    assert "test_sources_delegate_runtime_payload_builders" in content
    assert "test_diagnostic_export_route_delegates_response_helper" in content
    assert "test_diagnostic_export_route_response_accepts_explicit_clock" in content
    assert "hidden diagnostic-export clock dependencies in tests/callers" in content
    assert "bounded failure response decisions" in content
    assert "Flask response application in their dedicated helpers" in content
    assert "apply_job_diagnostics_defaults()" in content
    assert "app/diagnostics/runtime_payloads.py::safe_job_diagnostics_payload()" in content
    assert "test_job_diagnostics_payload_adds_defaults_without_setdefault" in content
    assert "test_safe_job_diagnostics_payload_owns_mapping_coercion_and_defaults" in content
    assert "test_job_diagnostics_defaults_helper_owns_payload_mutation" in content
    assert "route-local orchestration diagnostic default mutation" in content
    assert "mixed orchestration diagnostic lookup/coercion/defaulting" in content
    assert "runtime_payloads.py::resolved_health_checks()" in content
    assert "test_health_checks_mapping_owns_resolution_and_validation" in content
    assert "test_resolved_health_checks_owns_source_selection" in content
    assert "mixed runtime health-check source selection and type validation" in content
    assert "app/diagnostics/sources.py::_runtime_source()" in content
    assert "test_runtime_source_helper_owns_descriptor_defaults" in content
    assert "test_diagnostic_sanitization_policy_centralizes_source_bounds" in content
    assert "policy-owned source byte caps routed through the contract wrapper" in content
    assert "repeated runtime `DiagnosticSource` descriptor construction" in content
    assert "app/diagnostics/sources.py::_optional_runtime_source()" in content
    assert "_config_secret_source()" in content
    assert "_cache_stats_source()" in content
    assert "_recent_history_source()" in content
    assert "_dependency_collector()" in content
    assert "test_optional_runtime_source_helper_owns_missing_or_present_dependency" in content
    assert "test_dependency_collector_owns_dependency_capture" in content
    assert "test_optional_runtime_descriptor_helpers_own_fixed_source_shapes" in content
    assert "repeated fixed config/cache/history descriptor literals in the source-order builder" in content
    assert "inline optional dependency capture closures" in content
    assert "repeated optional dependency omitted/runtime branching" in content
    assert "app/diagnostics/sources.py::_orchestration_source()" in content
    assert "_omitted_orchestration_source()" in content
    assert "test_orchestration_source_helper_owns_request_branching" in content
    assert "test_omitted_orchestration_source_helper_owns_fixed_descriptor" in content
    assert "repeated fixed omitted orchestration descriptor literals" in content
    assert "inline orchestration diagnostic job/accessor branching" in content
    assert "app/diagnostics/sources.py::_default_source_context()" in content
    assert "test_default_source_context_owns_history_limit_and_timestamp" in content
    assert "inline metadata timestamp/history-limit normalization" in content
    assert "app/diagnostics/sources.py::_health_source()" in content
    assert "_health_payload_collector()" in content
    assert "test_health_source_helper_owns_dependency_capture" in content
    assert "test_health_payload_collector_owns_dependency_capture" in content
    assert "inline health source dependency-capture wiring in descriptor construction" in content
    assert "app/diagnostics/sources.py::_history_save_source()" in content
    assert "test_history_save_source_helper_owns_fixed_descriptor" in content
    assert "inline fixed history-save descriptor construction" in content
    assert "app/diagnostics/sources.py::_default_runtime_sources()" in content
    assert "test_default_runtime_sources_owns_source_ordering" in content
    assert "public default source factories that manually append ordered sources" in content
    assert "_safe_jsonish()" in content
    assert "_safe_mapping()" in content
    assert "_safe_jsonish_mapping()" in content
    assert "_safe_jsonish_sequence()" in content
    assert "_safe_jsonish_set()" in content
    assert "_append_safe_jsonish_item()" in content
    assert "sequence and set long paths share capped item accumulation" in content
    assert "test_safe_jsonish_helpers_own_container_and_default_coercion" in content
    assert "test_safe_mapping_uses_bounded_iteration_for_nested_mappings" in content
    assert "test_safe_jsonish_uses_direct_recursive_loops" in content
    assert "test_safe_jsonish_skips_iteration_for_exact_empty_single_pair_three_or_four_containers" in content
    assert "up to four values" in content
    assert "mapping items-view allocation" in content
    assert "mixed container traversal ownership in the jsonish dispatcher" in content
    assert "runtime payload helper bodies in the source descriptor factory" in content
    assert "whole-app diagnostic helper inputs" in content
    assert "route-local diagnostic timestamp wrappers" in content
    assert "successful diagnostic ZIP response assembly in the Flask route body" in content
    assert "bounded diagnostic failure response construction in the Flask route body" in content
    assert "recursive comprehension-frame allocation" in content
    assert "diagnostic source sanitization now applies mapping and sequence caps with bounded iteration" in content
    assert "Keep recent-history diagnostic payloads on bounded iteration." in content
    assert "runtime_payloads.py::recent_history_payload()" in content
    assert "recent_history_items()" in content
    assert "append_recent_history_item()" in content
    assert "calls runtime payload builders directly" in content
    assert "test_recent_history_payload_uses_bounded_iteration_not_slice" in content
    assert "test_recent_history_payload_accumulates_without_list_comprehension_frame" in content
    assert "test_recent_history_items_owns_safe_row_coercion" in content
    assert "public payload-builder ownership of row coercion" in content
    assert "helper-owned row append mutation" in content
    assert "comprehension-frame allocation" in content
    assert "recent-history diagnostic payloads now use bounded iteration over returned rows" in content
    assert "Keep diagnostic manifest duplicate-source validation single-pass." in content
    assert "DiagnosticManifest.__post_init__()" in content
    assert "app/diagnostics/contract.py::append_manifest_source()" in content
    assert "accepted iterable-source accumulation" in content
    assert "test_manifest_duplicate_source_validation_stops_at_first_duplicate" in content
    assert "diagnostic manifest deterministic serialization" in content
    assert "Keep diagnostic safe-error summary whitespace normalization on compiled regex." in content
    assert "_normalize_error_summary()" in content
    assert "test_safe_error_summary_normalizes_whitespace_without_split_list" in content
    assert "test_source_record_text_normalization_uses_shared_helper" in content
    assert "app/diagnostics/source_record_fields.py" in content
    assert "without re-exporting private field-helper functions or owner-only status/category vocabulary" in content
    assert "contract-facade re-exports of owner-only status/category/error-bound vocabulary" in content
    assert "_normalize_redaction_label()" in content
    assert "test_source_record_delegates_field_normalization_and_payload_builder" in content
    assert "dataclass-owned source-record field validation" in content
    assert "dataclass-owned source-record payload shaping" in content
    assert "nested redaction-label normalizer closures" in content
    assert "diagnostic source-record field validation and payload shaping now live in a dedicated contract helper" in content
    assert "duplicate local stripped-text helper logic" in content
    assert "diagnostic safe-error summary normalization now uses a compiled whitespace regex" in content
    assert "Keep diagnostic manifest aggregate serialization single-pass." in content
    assert "DiagnosticManifest.to_dict()" in content
    assert "app/diagnostics/manifest_payloads.py::manifest_payload()" in content
    assert "app/diagnostics/manifest_payloads.py::source_counts_payload()" in content
    assert "app/diagnostics/manifest_payloads.py::append_serialized_source()" in content
    assert "app/diagnostics/manifest_payloads.py::_add_and_append_source()" in content
    assert "paired count-and-append mutation for short and long manifest payload paths" in content
    assert "SourceCountsAccumulator" in content
    assert "test_manifest_reuses_construction_time_sorted_sources" in content
    assert "avoiding repeated sorting" in content
    assert "test_manifest_construction_skips_sort_for_zero_or_one_source" in content
    assert "test_manifest_serialization_computes_counts_in_one_source_pass" in content
    assert "test_manifest_to_dict_delegates_payload_builder" in content
    assert "reuses the source-record status vocabulary" in content
    assert "duplicate manifest-local source status literals" in content
    assert "test_manifest_payload_skips_iteration_for_empty_single_pair_three_or_four_sources" in content
    assert "fallback iteration for short manifest source tuples" in content
    assert "test_manifest_serialized_source_append_owns_record_serialization" in content
    assert "dataclass-owned aggregate manifest payload construction" in content
    assert "duplicated source-count branches across manifest and bundle summaries" in content
    assert "repeated source-record append mutation" in content
    assert "separate count-only source passes during manifest serialization" in content
    assert "test_source_record_serializes_redaction_labels_without_list_constructor" in content
    assert "source-record label serialization against `list(...)` constructor calls" in content
    assert "source-record label constructor copies" in content
    assert "test_redaction_label_normalization_uses_direct_accumulation" in content
    assert "test_redaction_label_normalization_skips_sort_for_zero_or_one_label" in content
    assert "delegates per-label text coercion to `_normalize_redaction_label()`" in content
    assert "set-comprehension frame" in content
    assert "unnecessary empty/single-item sorting during manifest construction and redaction-label normalization" in content
    assert "aggregate counts, redaction totals" in content
    assert "test_txt_field_parser_does_not_build_intermediate_field_list" in content
    assert "TXT field-list materialization" in content
    assert "Keep diagnostic bundle source preparation on streaming validation." in content
    assert "assemble_diagnostic_bundle()" in content
    assert "test_validation_stops_consuming_source_iterable_at_first_duplicate" in content
    assert "test_archive_entry_order_uses_explicit_extension" in content
    assert "starred archive-entry unpacking" in content
    assert "tuple generator expression over the archive entries" in content
    assert "archive-path generator frames" in content
    assert "DiagnosticBundle.summary" in content
    assert "app/diagnostics/archive_writer.py::write_stable_zip()" in content
    assert "test_archive_writer_owns_stable_zip_metadata" in content
    assert "assembler-owned stable ZIP writer mechanics" in content
    assert "app/diagnostics/bundle_layout.py" in content
    assert "keeping `DiagnosticSourceRecord` as a type-only contract import" in content
    assert "prepared-source ordering, payload-entry ordering, manifest-first archive entry layout, archive path projection, and summary aggregation" in content
    assert "append_archive_entry()" in content
    assert "append_archive_entry_path()" in content
    assert "long-path archive entry and path projection append mutation" in content
    assert "bundle summaries reuse shared aggregate counts without taking on accumulator internals" in content
    assert "without taking on accumulator internals or importing the contract at runtime for annotations" in content
    assert "test_single_source_bundle_skips_sorting" in content
    assert "unnecessary single-source/payload sorting" in content
    assert "test_bundle_summary_does_not_serialize_sources" in content
    assert "test_bundle_layout_owns_summary_and_ordering_helpers" in content
    assert "test_bundle_layout_owns_archive_entries_and_paths" in content
    assert "assembler-owned ordering/summary/archive-entry helper bodies" in content
    assert "private ordering compatibility wrappers" in content
    assert "app/diagnostics/records.py" in content
    assert "test_assembler_delegates_manifest_record_builders" in content
    assert (
        "importing source status/default reason vocabulary directly from "
        "`app/diagnostics/source_record_fields.py`"
        in content
    )
    assert "records imports source status vocabulary from the source-record field owner instead of the contract wrapper" in content
    assert "test_included_record_helper_owns_truncation_and_metadata" in content
    assert "app/diagnostics/source_results.py::source_collection_result()" in content
    assert "app/diagnostics/source_results.py::append_collected_source_result()" in content
    assert "keeping `DiagnosticSourceRecord` as a type-only contract import" in content
    assert "collect-plus-append mutation for long prepared-source paths" in content
    assert "test_source_collection_result_owns_per_source_outcomes" in content
    assert "test_source_collection_result_captures_errors_without_payload_entry" in content
    assert "test_collect_source_results_owns_record_and_payload_accumulation" in content
    assert "source-result type annotations do not import the contract, config-store protocol, or private prepared-source record at runtime" in content
    assert "assembler-owned per-source outcome branching" in content
    assert "assembler-owned source result accumulation" in content
    assert "source-result runtime imports of contract dataclasses, config-store protocol, and private prepared-source record for annotations only" in content
    assert "bundle-layout runtime imports of contract dataclasses for annotations only" in content
    assert "payload-encoding runtime imports of descriptor/redaction types for annotations only" in content
    assert "inline included record construction in the assembler loop" in content
    assert "assembler-owned manifest record helper bodies" in content
    assert "private record compatibility wrappers" in content
    assert "keeping redaction config/metadata types as type-only imports" in content
    assert "records runtime imports of redaction config/metadata types for annotations only" in content
    assert "records imports routed through the contract wrapper for source-record status/default vocabulary" in content
    assert "summary-time source serialization" in content
    assert "app/diagnostics/json_safe.py" in content
    assert "app/diagnostics/payload_encoding.py" in content
    assert "test_assembler_delegates_json_safe_payload_normalization" in content
    assert "test_json_safe_sequence_types_share_owner_recursive_helper" in content
    assert "test_json_safe_mapping_owns_direct_key_iteration" in content
    assert "safe_json_mapping()" in content
    assert "safe_json_sequence()" in content
    assert "app/diagnostics/json_safe.py::append_safe_json_item()" in content
    assert "long-path accumulation through" in content
    assert "test_json_safe_skips_iteration_for_exact_empty_single_pair_three_or_four_containers" in content
    assert "up to four values" in content
    assert "test_assembler_delegates_payload_collection_and_encoding" in content
    assert "descriptor/redaction type imports type-only" in content
    assert "runtime descriptor/redaction type imports out of assembler/payload encoding runtime paths" in content
    assert "test_text_payload_encoding_helper_owns_redacted_utf8_encoding" in content
    assert "test_json_payload_encoding_skips_text_encoding_helper" in content
    assert "test_json_payload_encoding_helper_owns_safe_json_encoding" in content
    assert "dispatcher-owned JSON-object redaction/encoding" in content
    assert "duplicated bytes/string redacted-text encoding" in content
    assert "assembler-owned recursive JSON-safe payload normalization" in content
    assert "private JSON-safe compatibility wrappers" in content
    assert "payload-encoding JSON-safe wrapper aliases" in content
    assert "assembler-owned collection/redaction/encoding decisions" in content
    assert "private payload compatibility wrappers" in content
    assert "test_json_safe_uses_direct_recursive_loops" in content
    assert "test_diagnostic_metadata_source_owns_payload_shape" in content
    assert "metadata source payload shape" in content
    assert "inline diagnostic metadata source payload construction" in content
    assert "metadata descriptor-owned payload schema literals" in content
    assert "test_diagnostic_source_text_normalization_uses_shared_helper" in content
    assert "test_diagnostic_modules_use_relative_sibling_imports" in content
    assert "diagnostics-internal package-facade sibling imports" in content
    assert (
        "importing source descriptor byte caps, category vocabulary, content-type default, text normalization, "
        "and integer normalization directly from `app/diagnostics/source_record_fields.py` instead of the contract wrapper"
        in content
    )
    assert "app/diagnostics/__init__.py` re-exports `DEFAULT_SOURCE_MAX_BYTES` from that same owner module" in content
    assert "test_diagnostic_sanitization_policy_centralizes_source_bounds" in content
    assert "app/diagnostics/source_preparation.py" in content
    assert "test_assembler_delegates_source_preparation" in content
    assert "source_preparation.py::_prepared_source()" in content
    assert "imports only the runtime `prepare_sources()` helper from the source-preparation owner" in content
    assert "keeps `DiagnosticSource`/`ConfigSecretStore` as type-only imports" in content
    assert "no longer imports the private `_PreparedSource` record type" in content
    assert "source-preparation imports routed through the contract wrapper for owner-module constants" in content
    assert "source descriptor byte/category/content-type semantics" in content
    assert "public package default-source-byte export compatibility" in content
    assert "package facade default-source-byte imports routed through the contract wrapper" in content
    assert "assembler-facade re-exports of the source descriptor owner type" in content
    assert "public archive-path compatibility constants, or `DiagnosticSource` through `__all__`" in content
    assert "test_prepared_source_helper_owns_normalized_record_construction" in content
    assert "inline prepared-source record construction in the preparation loop" in content
    assert "assembler runtime imports of source descriptor/config-store types for annotations only" in content
    assert "assembler runtime imports of private prepared-source record type" in content
    assert "assembler-owned descriptor validation state" in content
    assert "private source-preparation compatibility wrappers" in content
    assert "without re-exporting archive-path internals or compatibility constants" in content
    assert "test_assembler_uses_shared_diagnostic_sanitization_policy_bounds" in content
    assert "assembler-private archive-path re-exports" in content
    assert "assembler-facade archive-path compatibility constants" in content
    assert "diagnostic source descriptor validation now lives in a dedicated preparation module" in content
    assert "recursive mapping items-view allocation" in content
    assert "recursive comprehension frames during payload encoding" in content
    assert "diagnostic bundle deterministic archive ordering" in content
    assert "app/diagnostics/archive_paths.py" in content
    assert "Keep diagnostic archive path validation on single-pass segment scanning." in content
    assert "_iter_archive_path_segments()" in content
    assert "test_archive_path_validation_scans_segments_without_split_list" in content
    assert "diagnostic archive path validation now scans path segments once" in content
    assert "Keep diagnostic exact-secret redaction on preordered candidates." in content
    assert "app/diagnostics/secret_inventory.py" in content
    assert "explicit config-store factory" in content
    assert "text_rules.py::apply_exact_secret_redaction()" in content
    assert "test_exact_secret_redaction_reuses_preordered_candidates" in content
    assert "test_exact_secret_redaction_delegates_text_rule_helper" in content
    assert "test_redaction_metadata_reuses_sorted_label_snapshot" in content
    assert "test_configured_secret_collection_avoids_item_pairs_and_generator_frames" in content
    assert "test_configured_secret_collection_strips_each_secret_once" in content
    assert "test_configured_secret_candidate_append_owns_validation_and_construction" in content
    assert "test_candidate_label_tuple_owns_secret_label_projection" in content
    assert "test_configured_secret_collection_skips_sort_for_single_provider" in content
    assert "test_configured_secret_collection_accepts_explicit_store_factory" in content
    assert "hidden ConfigStore construction in tests/callers" in content
    assert "repeated configured-secret stripping" in content
    assert "repeated configured-secret candidate construction" in content
    assert "unnecessary single-item provider/label sorting" in content
    assert "provider item-pair sorting" in content
    assert "secret-label generator frames" in content
    assert "collector-owned candidate-label projection" in content
    assert "test_payload_redaction_uses_direct_recursive_loops" in content
    assert "redact_payload_sequence()" in content
    assert "test_payload_sequence_redaction_skips_iteration_for_empty_single_pair_three_or_four_sequence" in content
    assert "up to four values" in content
    assert "redact_payload_mapping()" in content
    assert "test_payload_mapping_redaction_owns_key_policy_and_child_traversal" in content
    assert "recursive payload items-view/list-comprehension allocation" in content
    assert "recursive traversal-owned mapping mechanics" in content
    assert "app/diagnostics/payload_redaction.py" in content
    assert "test_redaction_delegates_payload_traversal_engine" in content
    assert "test_redaction_facade_does_not_reexport_owner_module_internals" in content
    assert "redaction-module-owned payload traversal mechanics" in content
    assert "private payload traversal wrappers" in content
    assert "redaction-facade re-exports of owner-module public or private internals" in content
    assert "secret-inventory public APIs and internals" in content
    assert "private accumulator names, and secret-length policy constants" in content
    assert "redaction-module-owned exact replacement loops" in content
    assert "diagnostic payload traversal now lives in a dedicated payload-redaction helper" in content
    assert "app/diagnostics/payload_rules.py" in content
    assert "payload key-to-redaction-label classification" in content
    assert "test_payload_key_redaction_rules_live_outside_recursive_traversal" in content
    assert "recursive traversal-owned payload key classification" in content
    assert "test_configured_secret_inventory_deduplicates_provider_labels_directly" in content
    assert "provider label list-to-set copies" in content
    assert "unnecessary metadata label sorting" in content
    assert "test_redaction_metadata_skips_sort_for_zero_or_one_label" in content
    assert "skips `sorted()` entirely for empty or single-label metadata" in content
    assert "unnecessary metadata label sorting" in content
    assert "test_label_part_normalization_uses_compiled_regex" in content
    assert "test_config_secret_inventory_payload_accumulates_labels_without_list_constructor" in content
    assert "test_config_secret_inventory_payload_helper_owns_public_shape" in content
    assert "test_copy_label_tuple_delegates_long_path_append" in content
    assert "app/diagnostics/runtime_payloads.py::config_secret_inventory_payload_from_inventory()" in content
    assert "append_label_copy()" in content
    assert "long label-copy append mutation" in content
    assert "config_secret_inventory_payload_from_inventory()" in content
    assert "runtime source collection functions owning public payload shape" in content
    assert "label `list(...)` constructor calls" in content
    assert "diagnostic-source label constructor copies" in content
    assert "apply_text_pattern_redaction()` owns common credential regex rule coordination" in content
    assert "_apply_text_rule()" in content
    assert "test_apply_text_rule_owns_callback_replacement_counting" in content
    assert "mixed text-rule coordination and callback mechanics" in content
    assert "redact_text_with_candidates()" in content
    assert "test_text_pattern_redaction_delegates_rule_engine" in content
    assert "redaction-module-owned text regex replacement callbacks" in content
    assert "private text-rule wrappers" in content
    assert "redaction-module private text wrapper aliases" in content
    assert "diagnostic text credential pattern redaction now lives in a dedicated rule engine" in content
    assert "diagnostic provider-label normalization now reuses a compiled cleanup regex" in content
    assert "longest-secret-first exact replacement" in content
    assert "Keep normalized duplicate IOC candidates on the single-classification path in `run_pipeline()`." in content
    assert "pipeline-duplicate-candidates" in content
    assert "raw URL variants normalize to 1 IOC value" in content
    assert "test_clean_input_skips_defang_pattern_loop" in content
    assert "_DEFANG_PATTERNS" in content
    assert "test_defang_patterns_are_static_tuple" in content
    assert "IOC normalization now skips defang regex substitutions for already-clean values" in content
    assert "mutable static defang pattern tables" in content
    assert "calls `classify()` once" in content
    assert "test_normalized_duplicate_variants_classified_once" in content
    assert "test_type_value_duplicates_keep_first_output_order" in content
    assert "_candidate_raw()" in content
    assert "_classify_candidate_raw()" in content
    assert "_ioc_identity()" in content
    assert "test_pipeline_modules_use_relative_sibling_imports" in content
    assert "package-facade sibling imports in pipeline internals" in content
    assert "test_pipeline_dedup_rules_are_shared_helpers" in content
    assert "duplicated raw-candidate/classification/IOC-identity logic" in content
    assert "test_domain_lowercase_value_is_reused" in content
    assert "_DOMAIN_BLACKLIST" in content
    assert "test_domain_blacklist_uses_static_frozenset" in content
    assert "_classify_ip_type()" in content
    assert "test_ipv4_classification_parses_ip_once" in content
    assert "IP classification now parses candidates once" in content
    assert "domain classification now reuses one lowercase value" in content
    assert "final dict-values copy" in content
    assert "static blacklist set-literal allocation" in content
    assert "Keep raw IOC extraction deduplication on direct output-list accumulation." in content
    assert "app/pipeline/extractor.py::extract_iocs()" in content
    assert "_EXPECTED_EXTRACTION_ERRORS" in content
    assert "test_dedup_appends_first_seen_candidates_directly" in content
    assert "test_expected_extraction_errors_share_one_policy" in content
    assert "test_expected_extraction_errors_fail_closed_without_warning" in content
    assert "raw IOC extraction now appends first-seen candidates directly" in content
    assert "duplicated expected-exception tuples" in content
    assert "Keep `CacheStore.stats()` on one aggregate SQLite read." in content
    assert "cache-stats-query-count" in content
    assert "CacheStore.stats() executed 1 SELECT" in content
    assert "test_stats_uses_single_aggregate_query" in content
    assert "Keep nonpositive cache TTL reads on the pre-SQLite fast path." in content
    assert "ttl_seconds <= 0" in content
    assert "test_nonpositive_ttl_skips_cache_lookup" in content
    assert "nonpositive cache TTL reads now return before SQLite" in content
    assert "Keep empty cache read/write payloads on JSON literals." in content
    assert "app/json_utils.py::EMPTY_JSON_OBJECT" in content
    assert "CacheStore.put()" in content
    assert "test_empty_payload_skips_json_encoding" in content
    assert "CacheStore.get()" in content
    assert "get_all_for_ioc()" in content
    assert "test_empty_payload_skips_json_decoding" in content
    assert "test_empty_payload_uses_shared_json_literal_constant" in content
    assert "empty cache read/write payloads now use JSON literals" in content
    assert "cache detail reads now use direct row projection for up to four provider rows" in content
    assert "unnecessary JSON encoder and decoder calls for empty cache payloads" in content
    assert "duplicated JSON literal strings" in content
    assert "Keep cache/history SQLite PRAGMA setup behind the shared `app.sqlite.configure_connection()` helper." in content
    assert "tests/test_sqlite.py" in content
    assert "removing duplicated store initialization code" in content
    assert "Keep recent-history summaries on the SQL-side input preview projection." in content
    assert "app/enrichment/history_records.py" in content
    assert "_analysis_insert_record()" in content
    assert "test_save_analysis_delegates_insert_record_shaping" in content
    assert "test_history_store_public_exports_exclude_record_private_helpers" in content
    assert "history-store facade imports or re-exports of private record helpers" in content
    assert "store facade attributes and public exports" in content
    assert "HistoryStore-owned insert row shaping" in content
    assert "substr(input_text, 1, 120)" in content
    assert "test_truncates_input_text" in content
    assert "test_list_recent_empty_single_pair_and_three_paths_use_row_count" in content
    assert "direct row paths through four rows" in content
    assert "test_list_recent_accumulates_summaries_without_list_comprehension" in content
    assert "guards `list_recent()` against `<listcomp>` bytecode" in content
    assert "comprehension-frame allocation around bounded summary rows" in content
    assert "full history reload preserves the saved input" in content
    assert "Keep empty history save/load payloads on JSON literals." in content
    assert "_analysis_from_row()" in content
    assert "app/json_utils.py::EMPTY_JSON_ARRAY" in content
    assert "HistoryStore.save_analysis()" in content
    assert "test_empty_payloads_skip_json_encoding" in content
    assert "HistoryStore.load_analysis()" in content
    assert "test_empty_payloads_skip_json_decoding" in content
    assert "test_empty_payloads_use_shared_json_literal_constant" in content
    assert "empty history save/load payloads now use JSON literals" in content
    assert "unnecessary JSON encoder and decoder calls for empty saved payloads" in content
    assert "duplicated JSON literal strings" in content
    assert "Keep SSH auth.log parsing on streaming lines, direct BSD timestamps, and cached source classification." in content
    assert "app/ssh/line_streams.py" in content
    assert "decoded bytes/text stream iteration and CR/LF line-ending cleanup" in content
    assert "parse_auth_log()` calls `line_streams.iter_lines()` directly" in content
    assert "test_ssh_modules_use_relative_sibling_imports" in content
    assert "package-facade sibling imports for SSH auth.log uploads" in content
    assert "test_text_stream_is_not_read_all_at_once" in content
    assert "test_parser_delegates_line_stream_decoding_helpers" in content
    assert "test_bsd_timestamp_parsing_does_not_use_strptime" in content
    assert "test_repeated_source_classification_is_cached" in content
    assert "caches repeated source classification" in content
    assert "line-stream helper implementations drift back into the parser module" in content
    assert "Keep history top-verdict computation on the malicious short-circuit path." in content
    assert "_MAX_VERDICT" in content
    assert "_FALLBACK_VERDICT" in content
    assert "test_malicious_verdict_short_circuits_scan" in content
    assert "test_top_verdict_terminal_constants_are_precomputed" in content
    assert "test_short_top_verdict_paths_skip_iteration" in content
    assert "no-iteration fast paths up to four saved results" in content
    assert "history top-verdict computation now short-circuits" in content
    assert "duplicated terminal verdict literals" in content
    assert "Keep history verdict priority on a precomputed map." in content
    assert "_VERDICT_PRIORITY" in content
    assert "test_priority_map_is_precomputed" in content
    assert "repeated priority-map allocation" in content
    assert "Keep `ProviderRegistry` filters on direct provider scans." in content
    assert "test_all_accumulates_without_values_view" in content
    assert "append_registered_provider()" in content
    assert "test_all_delegates_registered_provider_append" in content
    assert "unnecessary values-view" in content
    assert "test_list_filters_do_not_allocate_comprehension_frames" in content
    assert "test_list_filters_scan_without_values_view" in content
    assert "append_configured_provider()" in content
    assert "append_provider_for_type()" in content
    assert "test_list_filters_delegate_append_mutation" in content
    assert "list-comprehension frames" in content
    assert "_provider_supports_configured_type" in content
    assert "test_providers_for_type_uses_shared_eligibility_predicate" in content
    assert "test_count_does_not_allocate_provider_list" in content
    assert "test_count_does_not_use_sum_generator" in content
    assert "test_count_scans_without_values_view" in content
    assert "test_count_uses_shared_eligibility_predicate" in content
    assert "duplicated configured/type eligibility logic" in content
    assert "registry scans now avoid provider values views and list-comprehension frames" in content
    assert "Keep static adapter frozensets on tuple inputs." in content
    assert "test_adapter_static_frozensets_avoid_temporary_set_literals" in content
    assert "temporary set-literal allocation" in content
    assert "static adapter membership frozensets now use tuple inputs" in content
    assert "Keep ThreatFox best-record selection on a short-circuiting confidence scan." in content
    assert "app/enrichment/adapters/abusech.py::abusech_data_records()" in content
    assert "_select_best_record()" in content
    assert "_threatfox_verdict()" in content
    assert "_threatfox_raw_stats()" in content
    assert "app/enrichment/adapters/threatfox.py::_threatfox_result()" in content
    assert "test_best_record_selection_short_circuits_on_perfect_confidence" in content
    assert "test_best_record_selection_skips_iteration_for_zero_to_four_records" in content
    assert "test_parse_response_delegates_verdict_and_raw_stats_helpers" in content
    assert "tests/test_abusech.py::test_data_records_preserve_no_result_and_missing_data_contract" in content
    assert "test_raw_stats_helper_preserves_key_order_and_values" in content
    assert "test_verdict_helper_preserves_confidence_threshold" in content
    assert "tests/test_threatfox.py::TestEdgeCases::test_result_helper_preserves_provider_envelope" in content
    assert "ThreatFox result construction now uses one provider envelope helper" in content
    assert "parser-owned abuse.ch query-status/data-list normalization" in content
    assert "parser-owned confidence verdicting/raw_stats construction" in content
    assert "Keep ASN TXT parsing on first-record and direct field extraction." in content
    assert "CymruASNAdapter.lookup()" in content
    assert "_cymru_query_name()" in content
    assert "_configured_resolver()" in content
    assert "_asn_raw_stats()" in content
    assert "test_lookup_delegates_dns_query_name_helper" in content
    assert "test_configured_resolver_helper_preserves_lifetime_policy" in content
    assert "test_query_name_helper_preserves_ipv4_and_ipv6_zones" in content
    assert "test_txt_answer_uses_first_record_without_materializing_all_answers" in content
    assert "decode_txt_chunks()" in content
    assert "test_short_chunk_txt_answers_skip_join_iteration" in content
    assert "test_multi_chunk_txt_answer_still_concatenates_segments" in content
    assert "test_txt_parse_does_not_allocate_split_parts" in content
    assert "test_parse_response_delegates_raw_stats_helper" in content
    assert "test_raw_stats_helper_preserves_key_order_and_values" in content
    assert "shared TXT chunk decoder" in content
    assert "raw_stats shaping is delegated to one helper" in content
    assert "test_no_data_result_helper_preserves_informational_shape" in content
    assert "lookup-owned reverse-pointer zone replacement rules" in content
    assert "lookup-owned resolver setup" in content
    assert "adapter-local TXT chunk mechanics" in content
    assert "parser-owned ASN raw_stats mechanics" in content
    assert "duplicated no-data result construction" in content
    assert "no-HTTP/no-requests boundaries" in content
    assert "Keep DNS record extraction on table-driven dispatch." in content
    assert "DnsAdapter.lookup()" in content
    assert "_configured_resolver()" in content
    assert "_empty_raw_stats()" in content
    assert "_resolve_record_type()" in content
    assert "app/enrichment/adapters/dns_lookup.py::_dns_result()" in content
    assert "test_lookup_uses_record_table_extractors" in content
    assert "test_lookup_delegates_raw_stats_and_record_resolution_helpers" in content
    assert "test_configured_resolver_helper_preserves_lifetime_policy" in content
    assert "test_empty_raw_stats_helper_preserves_key_order_and_fresh_lists" in content
    assert "test_record_resolution_helper_preserves_error_mapping" in content
    assert "test_record_resolution_helper_preserves_expected_empty_outcomes" in content
    assert "test_short_chunk_txt_records_skip_join_iteration" in content
    assert "test_record_extractors_do_not_allocate_list_comprehension_frames" in content
    assert "test_record_extractors_skip_iteration_for_empty_single_pair_three_or_four_answers" in content
    assert "direct paths for up to four answers" in content
    assert "DNS lookup now uses table-driven extractors plus shared raw_stats" in content
    assert "lookup-owned resolver setup" in content
    assert "lookup-owned raw_stats initialization" in content
    assert "lookup-owned DNS exception mapping" in content
    assert "adapter-local TXT chunk mechanics" in content
    assert "list-comprehension extractor frames" in content
    assert "tests/test_dns_lookup.py::TestSuccessfulLookup::test_result_helper_preserves_provider_envelope" in content
    assert "DNS result construction now uses one informational provider envelope helper" in content
    assert "Keep VirusTotal engine total computation in the stats scan." in content
    assert "virustotal.py::_parse_response()" in content
    assert "_analysis_map()" in content
    assert "_engine_counts()" in content
    assert "_virustotal_verdict()" in content
    assert "_scan_date()" in content
    assert "_top_detections()" in content
    assert "_virustotal_raw_stats()" in content
    assert "BaseHTTPAdapter._make_pre_raise_hook()" in content
    assert "_rate_limit_on_429` class flag" in content
    assert "VTAdapter.supported_types" in content
    assert "app/enrichment/adapters/virustotal.py::_virustotal_result()" in content
    assert "test_total_engine_count_does_not_use_sum_helper" in content
    assert "test_engine_status_exclusions_use_static_frozenset" in content
    assert "test_top_detections_do_not_allocate_values_view" in content
    assert "test_parse_response_delegates_stats_verdict_and_raw_stats_helpers" in content
    assert "test_adapter_uses_base_lookup_with_status_hook" in content
    assert "test_shared_429_helper_returns_rate_limit_error" in content
    assert "test_engine_counts_and_verdict_helper_preserve_semantics" in content
    assert "test_top_detections_helper_preserves_unique_cap" in content
    assert "test_raw_stats_helper_preserves_stats_and_reputation" in content
    assert "stats items-view allocation" in content
    assert "per-parse excluded-status set construction" in content
    assert "analysis-result values-view allocation" in content
    assert "parser-owned stats/verdict/raw_stats mechanics" in content
    assert "provider-local generic 404/429 hook logic" in content
    assert "duplicated lookup/safe_request dispatch" in content
    assert "tests/test_vt_adapter.py::test_supported_types_derive_from_endpoint_map" in content
    assert "tests/test_vt_adapter.py::TestLookupSuccess::test_result_helper_preserves_provider_envelope" in content
    assert "VirusTotal now uses the shared HTTP lookup pipeline, shared 404/429 status helpers" in content
    assert "top detections, reputation" in content
    assert "Keep ThreatMiner capped result extraction bounded." in content
    assert "app/enrichment/adapters/threatminer.py" in content
    assert "_has_results()" in content
    assert "_threatminer_request_url()" in content
    assert "_passive_dns_raw_stats()" in content
    assert "_samples_raw_stats()" in content
    assert "_domain_raw_stats()" in content
    assert "test_ip_lookup_passive_dns_stops_at_cap" in content
    assert "test_zero_cap_passive_dns_skips_result_iteration" in content
    assert "test_empty_single_pair_three_and_four_passive_dns_lists_skip_accumulator_loop" in content
    assert "test_zero_cap_samples_skip_result_iteration" in content
    assert "test_empty_single_pair_three_and_four_sample_lists_skip_accumulator_loop" in content
    assert "short result lists up to four rows avoid fallback iteration" in content
    assert "test_call_delegates_request_url_construction" in content
    assert "test_request_url_helper_preserves_query_shape" in content
    assert "test_lookup_paths_delegate_result_gates_and_raw_stats_helpers" in content
    assert "test_result_body_gate_preserves_404_and_empty_semantics" in content
    assert "test_raw_stats_helpers_preserve_public_shapes" in content
    assert "test_domain_raw_stats_omits_empty_extracted_lists" in content
    assert "ThreatMiner lookup paths now share result-body gates and raw_stats helpers" in content
    assert "dispatch-owned request URL construction" in content
    assert "repeated lookup-path body gates" in content
    assert "lookup-owned raw_stats dictionary assembly" in content
    assert "zero-cap result iteration" in content
    assert "test_dict_sample_rows_do_not_allocate_values_view" in content
    assert "dict values-view allocation" in content
    assert "test_no_data_result_helper_preserves_informational_shape" in content
    assert "full oversized result scans" in content
    assert "duplicated no-data result construction" in content
    assert "Keep crt.sh certificate parsing on one body scan." in content
    assert "app/enrichment/adapters/base.py::BaseHTTPAdapter.lookup()" in content
    assert "app/enrichment/adapters/crtsh.py::_parse_response()" in content
    assert "_crtsh_raw_stats()" in content
    assert "app/enrichment/adapters/crtsh.py::_crtsh_result()" in content
    assert "test_successful_json_list_body_is_parsed" in content
    assert "test_adapter_uses_base_lookup_for_json_list_response" in content
    assert "test_date_range_and_subdomains_computed_in_one_body_scan" in content
    assert "test_parse_response_delegates_raw_stats_helper" in content
    assert "test_raw_stats_helper_preserves_key_order_and_values" in content
    assert "test_name_value_parsing_does_not_allocate_split_list" in content
    assert "test_empty_or_single_subdomain_sets_skip_sorting" in content
    assert "test_four_subdomain_sets_skip_sorting" in content
    assert "short multi-subdomain sets up to four entries" in content
    assert "test_subdomain_cap_avoids_full_sorted_list" in content
    assert "test_result_helper_preserves_provider_envelope" in content
    assert "crt.sh certificate parsing now delegates raw_stats shaping" in content
    assert "crt.sh now uses the shared HTTP lookup pipeline for JSON-list responses" in content
    assert "crt.sh subdomain selection now skips sorting empty, single-subdomain, and short multi-subdomain sets up to four entries" in content
    assert "duplicated crt.sh lookup/safe_request dispatch" in content
    assert "parser-owned certificate raw_stats mechanics" in content
    assert "wildcard stripping" in content
    assert "per-certificate SAN split-list allocation" in content
    assert "unnecessary empty/single subdomain sorting" in content
    assert "full oversized subdomain sorting" in content
    assert "Keep Shodan malicious-tag detection on a direct count." in content
    assert "app/enrichment/adapters/shodan.py::_parse_response()" in content
    assert "_shodan_signals()" in content
    assert "_shodan_verdict()" in content
    assert "_malicious_tag_count()" in content
    assert "_raw_stats()" in content
    assert "_no_data_on_404` class flag" in content
    assert "test_malicious_tag_count_preserves_duplicate_bad_tags" in content
    assert "test_parse_response_delegates_raw_stats_and_tag_count_helpers" in content
    assert "test_shodan_signal_helper_preserves_list_identity_and_defaults" in content
    assert "test_verdict_helper_preserves_priority_and_counts" in content
    assert "test_raw_stats_helper_preserves_list_identity_and_key_order" in content
    assert "test_malicious_tag_count_preserves_short_no_iteration_paths" in content
    assert "short-list tag-count paths up to four tags" in content
    assert "test_shared_404_hook_returns_no_data_result" in content
    assert "test_generic_status_policy_flags_build_shared_hook" in content
    assert "test_result_helper_preserves_provider_envelope" in content
    assert "Shodan now uses the base adapter's generic 404 no-data policy flag" in content
    assert "intermediate bad-tag list allocation" in content
    assert "parser-owned signal extraction" in content
    assert "parser-owned verdict branching" in content
    assert "provider-local generic 404 hook methods" in content
    assert "duplicated verdict-branch raw_stats construction" in content
    assert "Keep EmailRep malicious verdict selection on the risk-flag scan." in content
    assert "app/enrichment/adapters/emailrep.py::_risk_flags()" in content
    assert "_emailrep_signals()" in content
    assert "_emailrep_verdict()" in content
    assert "_emailrep_detection_count()" in content
    assert "_emailrep_raw_stats()" in content
    assert "app/enrichment/adapters/emailrep.py::_emailrep_result()" in content
    assert "test_verdict_uses_risk_flag_scan_without_second_malicious_pass" in content
    assert "test_verdict_membership_tables_are_static_frozensets" in content
    assert "test_parse_response_delegates_verdict_count_and_raw_stats_helpers" in content
    assert "test_signal_helper_preserves_defaults_and_details_reuse" in content
    assert "test_verdict_and_detection_helpers_preserve_semantics" in content
    assert "test_raw_stats_helper_preserves_key_order_and_list_identity" in content
    assert "test_profiles_helper_reuses_lists_and_normalizes_missing_values" in content
    assert "tests/test_emailrep.py::TestEmailRepLookup::test_result_helper_preserves_provider_envelope" in content
    assert "EmailRep malicious verdict selection now reuses the ordered risk-flag scan" in content
    assert "parsing delegates verdict/count/raw_stats mechanics" in content
    assert "response-field defaults" in content
    assert "parser-owned response-field extraction" in content
    assert "per-parse verdict membership set construction" in content
    assert "parser-owned verdict/count/raw_stats mechanics" in content
    assert "Keep AbuseIPDB parsed result construction behind one provider envelope helper." in content
    assert "_abuseipdb_signals()" in content
    assert "_abuseipdb_verdict()" in content
    assert "_abuseipdb_raw_stats()" in content
    assert "_rate_limit_on_429` class flag" in content
    assert "app/enrichment/adapters/abuseipdb.py::_abuseipdb_result()" in content
    assert "test_parse_response_delegates_verdict_and_raw_stats_helpers" in content
    assert "test_signal_helper_preserves_data_defaults_and_identity" in content
    assert "test_verdict_helper_preserves_thresholds" in content
    assert "test_raw_stats_helper_preserves_key_order_and_values" in content
    assert "test_shared_429_helper_returns_rate_limit_error" in content
    assert "test_generic_status_policy_flags_build_shared_hook" in content
    assert "tests/test_abuseipdb.py::TestAbuseIPDBLookup::test_result_helper_preserves_provider_envelope" in content
    assert "AbuseIPDB now uses the base adapter's generic 429 rate-limit policy flag" in content
    assert "data-envelope defaults and identity" in content
    assert "provider-local generic 429 hook methods" in content
    assert "parser-owned data-envelope extraction" in content
    assert "parser-owned score branching" in content
    assert "parser-owned raw_stats envelope construction" in content
    assert "Keep IP Context geo and ASN/ISP formatting on direct string construction." in content
    assert "app/enrichment/adapters/ip_api.py::_parse_response()" in content
    assert "_ip_context_signals()" in content
    assert "_asn_context()" in content
    assert "_geo_context()" in content
    assert "_raw_stats()" in content
    assert "test_parser_delegates_geo_and_raw_stats_helpers" in content
    assert "test_signal_helper_preserves_defaults_and_flags_identity" in content
    assert "test_geo_format_exact_full_context" in content
    assert "test_org_parsing_does_not_allocate_split_parts" in content
    assert "test_asn_context_uses_partition_without_split" in content
    assert "test_geo_context_builds_without_parts_list" in content
    assert "test_raw_stats_helper_preserves_flags_identity_and_key_order" in content
    assert "test_no_data_result_helper_preserves_informational_shape" in content
    assert "raw_stats key order/flags identity" in content
    assert "missing-country no-data behavior" in content
    assert "parser-owned response-field extraction" in content
    assert "parser-owned formatting/raw_stats mechanics" in content
    assert "temporary geo-part and ASN/ISP split-list allocation" in content
    assert "duplicated no-data result construction" in content
    assert "Keep WHOIS name-server normalization on list reuse." in content
    assert "app/enrichment/adapters/whois_lookup.py::_normalise_name_servers()" in content
    assert "_whois_raw_stats()" in content
    assert "_safe_whois_field()" in content
    assert "app/enrichment/adapters/whois_lookup.py::_whois_result()" in content
    assert "test_lookup_delegates_successful_raw_stats_extraction" in content
    assert "test_whois_raw_stats_helper_preserves_shape_and_list_identity" in content
    assert "test_whois_raw_stats_helper_records_parse_errors" in content
    assert "test_name_server_lists_are_reused_without_copying" in content
    assert "test_normalise_name_servers_skips_iteration_for_empty_single_pair_three_or_four_tuple" in content
    assert "lookup-owned field extraction try/except blocks" in content
    assert "tests/test_whois_lookup.py::TestSuccessfulLookup::test_result_helper_preserves_provider_envelope" in content
    assert "WHOIS result construction now uses one informational provider envelope helper" in content
    assert "Keep shared HTTP response reads on one byte accumulator." in content
    assert "app/enrichment/http_safety.py::read_limited()" in content
    assert "test_read_limited_parses_chunked_json" in content
    assert "test_read_limited_uses_shared_chunk_size_constant" in content
    assert "chunk-list allocation" in content
    assert "Keep HTTP adapter allowlist membership on a construction-time set." in content
    assert "app/enrichment/adapters/base.py::BaseHTTPAdapter.__init__()" in content
    assert "test_allowed_hosts_are_cached_as_membership_set" in content
    assert "test_single_pair_three_or_four_allowed_hosts_skip_general_iteration" in content
    assert "skips the no-op `Session.headers.update({})`" in content
    assert "test_default_auth_headers_skip_empty_session_update" in content
    assert "test_auth_headers_snapshot_accumulates_without_constructor_copy" in content
    assert "test_adapter_auth_header_cache_uses_immutable_snapshot" in content
    assert "auth-header constructor copies" in content
    assert "no-op empty header updates" in content
    assert "HTTP adapters now cache allowed-host membership as a frozenset" in content
    assert "Keep route-mapped adapter support declarations derived from endpoint maps." in content
    assert "test_supported_types_derive_from_hash_route_map" in content
    assert "_hashlookup_signals()" in content
    assert "_hashlookup_raw_stats()" in content
    assert "test_signal_helper_preserves_defaults" in content
    assert "test_raw_stats_helper_preserves_key_order_and_defaults" in content
    assert "app/enrichment/adapters/hashlookup.py::_hashlookup_result()" in content
    assert "tests/test_hashlookup.py::TestLookupFound::test_result_helper_preserves_provider_envelope" in content
    assert "test_supported_types_derive_from_otx_route_map" in content
    assert "_no_data_on_404` class flags" in content
    assert "test_generic_status_policy_flags_build_shared_hook" in content
    assert "_otx_signals()" in content
    assert "_otx_verdict()" in content
    assert "_otx_raw_stats()" in content
    assert "test_parse_response_delegates_verdict_and_raw_stats_helpers" in content
    assert "test_signal_helper_preserves_defaults_and_pulse_mapping" in content
    assert "test_verdict_helper_preserves_thresholds" in content
    assert "test_raw_stats_helper_preserves_key_order_and_values" in content
    assert "test_shared_404_hook_ignores_other_statuses" in content
    assert "test_supported_types_derive_from_endpoint_map" in content
    assert "app/enrichment/adapters/otx.py::_otx_result()" in content
    assert "tests/test_otx.py::TestOTXLookup::test_result_helper_preserves_provider_envelope" in content
    assert "app/enrichment/adapters/abusech.py::abusech_query_status()" in content
    assert "_urlhaus_signals()" in content
    assert "_urlhaus_verdict()" in content
    assert "_urlhaus_raw_stats()" in content
    assert "tests/test_abusech.py::test_query_status_helper_preserves_provider_fallback" in content
    assert "test_signal_helper_preserves_defaults_and_metadata_identity" in content
    assert "test_verdict_helper_preserves_status_and_count_semantics" in content
    assert "test_raw_stats_helper_preserves_key_order_and_blacklist_identity" in content
    assert "app/enrichment/adapters/urlhaus.py::_urlhaus_result()" in content
    assert "tests/test_urlhaus.py::TestURLhausLookup::test_result_helper_preserves_provider_envelope" in content
    assert "route-mapped HTTP adapters now derive supported IOC types from endpoint maps" in content
    assert "Hashlookup/OTX use the base adapter's generic 404 no-data policy flag" in content
    assert "Hashlookup/OTX/URLhaus parsing delegates raw_stats/verdict mechanics" in content
    assert "result construction uses provider envelope helpers" in content
    assert "parser-owned Hashlookup response-field extraction/raw_stats mechanics" in content
    assert "OTX response-field defaults" in content
    assert "parser-owned OTX response-field extraction" in content
    assert "parser-owned OTX threshold/raw_stats mechanics" in content
    assert "URLhaus response-field defaults" in content
    assert "URLhaus metadata identity" in content
    assert "parser-owned URLhaus response-field extraction" in content
    assert "parser-owned URLhaus query-status/verdict/raw_stats mechanics" in content
    assert "Keep MalwareBazaar result construction behind one provider envelope helper." in content
    assert "_malwarebazaar_raw_stats()" in content
    assert "app/enrichment/adapters/malwarebazaar.py::_malwarebazaar_result()" in content
    assert "test_parse_response_delegates_raw_stats_helper" in content
    assert "tests/test_abusech.py::test_data_records_preserve_not_found_and_missing_data_contract" in content
    assert "test_raw_stats_helper_preserves_key_order_and_tag_identity" in content
    assert "test_result_helper_preserves_provider_envelope" in content
    assert "MalwareBazaar parsing now delegates raw malware metadata shaping" in content
    assert "parser-owned raw_stats envelope construction" in content
    assert "Keep GreyNoise result construction behind one provider envelope helper." in content
    assert "_greynoise_signals()" in content
    assert "_greynoise_verdict()" in content
    assert "_greynoise_raw_stats()" in content
    assert "_no_data_on_404` class flag" in content
    assert "app/enrichment/adapters/greynoise.py::_greynoise_result()" in content
    assert "test_parse_response_delegates_verdict_and_raw_stats_helpers" in content
    assert "test_signal_helper_preserves_defaults_and_key_fallbacks" in content
    assert "test_verdict_helper_preserves_priority" in content
    assert "test_raw_stats_helper_preserves_key_order_and_values" in content
    assert "GreyNoise result construction now uses one provider envelope helper" in content
    assert "provider-local generic 404 hook methods" in content
    assert "parser-owned signal extraction" in content
    assert "parser-owned verdict branching" in content
    assert "parser-owned raw_stats envelope construction" in content
    assert "Keep ConfigStore read-after-write on the cached parser path." in content
    assert "app/enrichment/config_store.py::_save_config()" in content
    assert "app/enrichment/config_files.py" in content
    assert "app/enrichment/config_values.py" in content
    assert "path-scoped locks, mutable parser copying, and atomic owner-only writes" in content
    assert "without retaining private file-helper aliases" in content
    assert "without retaining private value-helper aliases" in content
    assert "test_save_keeps_written_config_cached" in content
    assert "test_config_store_delegates_file_mechanics_to_config_files" in content
    assert "test_config_store_delegates_value_helpers" in content
    assert "test_config_copy_accumulates_sections_without_constructor_copies" in content
    assert "parser-copy dict-comprehension frames" in content
    assert "test_all_provider_keys_accumulates_directly_from_section" in content
    assert "append_provider_key()" in content
    assert "test_provider_key_fallback_delegates_append_mutation" in content
    assert "test_provider_key_get_and_set_share_option_normalization" in content
    assert "ConfigStore-owned file-lock/tempfile mechanics" in content
    assert "ConfigStore-owned value normalization and TTL parsing" in content
    assert "provider-section constructor copies" in content
    assert "direct short paths for up to four configured providers" in content
    assert "duplicated provider option-name normalization" in content
    assert "immediate read-after-write paths do not reparse disk" in content
    assert "ConfigStore value normalization, TTL parsing, and provider-section accumulation now live in config value helpers" in content
    assert "Keep registry provider-key loading on one config map read." in content
    assert "PROVIDER_REGISTRATION_PLAN" in content
    assert "ProviderRegistration" in content
    assert "registration-kind constants" in content
    assert "test_adapter_modules_use_relative_enrichment_imports" in content
    assert "package-facade sibling imports in adapter modules" in content
    assert "adapter-owner public imports" in content
    assert "catalog-facade public attributes or re-exports of concrete adapter classes" in content
    assert "retaining private setup-module aliases for catalog tables" in content
    assert "parallel split catalog tables" in content
    assert "app/enrichment/setup.py::build_registry()" in content
    assert "_register_keyed_provider()" in content
    assert "_register_zero_auth_provider()" in content
    assert "_register_direct_provider()" in content
    assert "_register_provider_from_plan()" in content
    assert "test_config_store_all_provider_keys_called_once_for_key_providers" in content
    assert "test_key_required_providers_share_registration_helper" in content
    assert "test_zero_auth_http_providers_share_registration_helper" in content
    assert "test_non_http_zero_auth_providers_use_direct_registration_helper" in content
    assert "test_provider_registration_tables_preserve_order_without_slices" in content
    assert "all 16 registered providers" in content
    assert "direct DNS/ASN/WHOIS setup" in content
    assert "removal of split catalog registration tables" in content
    assert "unified registration-plan order" in content
    assert "named registration records" in content
    assert "provider registry setup now walks one catalog-owned registration plan" in content
    assert "security scanner JSON finding serialization now shares one append helper" in content
    assert "runtime-state boundary JSON serialization now shares append helpers" in content
    assert "runtime-state repair JSON action serialization now shares one append helper" in content
    assert "split provider-order registration loops" in content
    assert "duplicated keyed-provider construction paths" in content
    assert "unused HTTP allowlist constructor arguments on non-HTTP adapters" in content
    assert "duplicated zero-auth HTTP construction paths" in content
    assert "setup-module metadata re-export aliases" in content
    assert "positional registration tuple dispatch" in content
    assert "inline registration-kind string branching" in content
    assert "Keep settings provider-key display on one config map read." in content
    assert "app/routes/settings.py::settings_get()" in content
    assert "app/routes/settings_view.py" in content
    assert "settings provider status rows, local provider health rows" in content
    assert "without re-exporting settings view compatibility aliases" in content
    assert "instead of retaining private action aliases in the route module" in content
    assert "settings_view.py::settings_page_context()" in content
    assert "settings_view.py::settings_route_context()" in content
    assert "settings_page_result()" in content
    assert "shared `TemplateResult` response boundary" in content
    assert "route-supplied cache/registry dependencies" in content
    assert "passes cache/registry dependencies explicitly" in content
    assert "settings_view.py::positive_cache_ttl_hours()" in content
    assert "settings_view.py::save_provider_key_and_rebuild_registry()" in content
    assert "settings_view.py::provider_key_save_action()" in content
    assert "settings_view.py::provider_key_save_action_from_form()" in content
    assert "provider_key_save_route_response()" in content
    assert "settings_view.py::apply_settings_action()" in content
    assert "settings_view.py::apply_settings_action_response()" in content
    assert "explicit setter instead of accepting the whole Flask app" in content
    assert "explicit registry-setter forwarding" in content
    assert "settings_view.py::cache_ttl_update_action()" in content
    assert "settings_view.py::cache_ttl_update_action_from_form()" in content
    assert "cache_ttl_update_route_response()" in content
    assert "settings_view.py::cache_clear_action()" in content
    assert "cache_clear_route_response()" in content
    assert "settings action flash message text" in content
    assert "browser_responses.py::apply_flash_redirect()" in content
    assert "settings_view.py::apply_settings_action_response()" in content
    assert "save_provider_key()" in content
    assert "app/routes/settings_view.py::_mask_key()" in content
    assert "test_get_settings_reads_provider_key_map_once" in content
    assert "test_settings_route_delegates_provider_rows_to_view_helpers" in content
    assert "test_settings_page_context_owns_get_template_shape" in content
    assert "test_save_provider_key_helper_preserves_vt_and_provider_paths" in content
    assert "test_save_provider_key_and_registry_rebuild_lives_in_view_helper" in content
    assert "test_provider_key_save_action_from_form_owns_field_normalization" in content
    assert "test_provider_key_save_route_response_owns_action_application" in content
    assert "test_provider_key_save_action_owns_post_validation_and_registry_rebuild" in content
    assert "test_apply_settings_action_owns_optional_registry_assignment" in content
    assert "test_apply_settings_action_response_preserves_flash_redirect_and_registry_assignment" in content
    assert "test_positive_cache_ttl_helper_owns_ttl_validation" in content
    assert "test_cache_ttl_update_action_owns_validation_and_save" in content
    assert "test_cache_ttl_update_route_response_owns_action_application" in content
    assert "test_cache_clear_action_owns_cache_clear_and_result" in content
    assert "test_cache_clear_route_response_owns_action_application" in content
    assert "test_settings_action_response_application_lives_in_view_helper" in content
    assert "test_provider_status_rows_accumulates_without_constructor_copy" in content
    assert "test_provider_health_row_helper_owns_secret_free_shape" in content
    assert "test_mask_key_measures_configured_key_once" in content
    assert "masked key display" in content
    assert "repeated configured-key length work" in content
    assert "provider-info constructor copies" in content
    assert "repeated provider status row construction mechanics" in content
    assert "repeated provider health row literal construction" in content
    assert "route-local provider view-model construction" in content
    assert "route-owned settings GET template-context assembly" in content
    assert "settings_page_route_response()" in content
    assert "route-owned settings GET result construction" in content
    assert "route-owned settings GET response application" in content
    assert "whole-app settings helper inputs" in content
    assert "whole-app settings action-response inputs" in content
    assert "route-local provider-key action construction" in content
    assert "route-local cache-TTL action construction" in content
    assert "route-local cache-clear action construction" in content
    assert "route-local cache TTL parsing" in content
    assert "route-local cache TTL save execution" in content
    assert "route-local cache clear execution" in content
    assert "route-local provider key save branching" in content
    assert "route-local provider save validation" in content
    assert "route-local optional registry assignment" in content
    assert "route-local settings flash text" in content
    assert "route-local settings flash/redirect response application" in content
    assert "repeated settings flash/redirect plumbing" in content
    assert "route-local ConfigStore construction for key saves" in content
    assert "route-local ConfigStore construction for TTL saves" in content
    assert "route-local provider registry rebuild construction" in content
    assert "Keep settings provider validation on a precomputed ID set." in content
    assert "provider_catalog.py::valid_provider_ids()" in content
    assert "app/routes/settings.py::_VALID_PROVIDER_IDS" in content
    assert "app/routes/form_values.py::stripped_form_value()" in content
    assert "direct helper loop" in content
    assert "test_valid_provider_ids_reuse_catalog_helper_without_route_list_builder" in content
    assert "test_save_provider_validation_uses_precomputed_id_set" in content
    assert "test_settings_post_and_cache_ttl_share_form_normalization" in content
    assert "test_settings_form_normalization_lives_in_shared_route_helper" in content
    assert "generator/set-comprehension frames" in content
    assert "provider-id set construction" in content
    assert "duplicate provider-id metadata tuples" in content
    assert "duplicated form-value normalization" in content
    assert "route-local request form access/trimming mechanics" in content
    assert "IOC pipeline duplicate-candidate work until the top analyst-loop seams" not in content
    assert "broader SQLite cache/history access shape still needs contention evidence" in content
    assert "R086" in content
    assert "R088" in content
    assert "Measure browser result rendering churn after the status/fan-out target" not in content
    assert "browser result rendering churn remains important, but should follow" not in content
    assert "M017 follow-up should focus on remaining flush-wide" not in content
    assert "unresolved S04 target" not in content
    assert "do-next S04 target" not in content
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


def test_m020_baseline_uses_aggressive_rewrite_contract(tmp_path):
    output_path = tmp_path / "m020-audit.md"

    result = run_audit(
        "--milestone-id",
        "M020",
        "--mode",
        "baseline",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    content = output_path.read_text(encoding="utf-8")
    assert "# M020 Optimization Audit — SentinelX" in content
    assert "## M020 aggressive rewrite contract" in content
    assert "docs/project-map.md" in content
    assert "audit-led aggressive refactor and deep optimization" in content
    assert "D081" in content
    assert "D082" in content
    assert "D083" in content
    assert "R094" in content
    assert "R095" in content
    assert "R099" in content
    assert "R100" in content
    assert "R101" in content
    assert "R102" in content
    assert "R103" in content
    assert "deferred-scope" in content
    assert "storage redesign" in content
    assert "major UI/product redesign" in content
    assert "external provider integration" in content
    assert "constraints, not shipped optimizations" in content
    assert "No new storage redesign" in content
    assert "No broad UI/product redesign" in content
    assert "No external provider integration" in content
    assert "S01 produces this generated audit artifact" in content
    assert "S02 consumed the highest-confidence route-helper candidate" in content
    assert "S05 refreshes final shipped/rejected outcomes" in content
    assert "### do now" in content
    assert "### do next" in content
    assert "### later" in content
    assert "### leave alone" in content
    assert "Keep S02's duplicate route IOC grouping rewrite on the shared IOC payload seam" in content
    assert "app/routes/ioc_payloads.py" in content
    assert "S02 route/API/history contract" in content
    assert "analyst-visible route/API/history contract" in content
    assert "app/routes/analysis.py" in content
    assert "app/routes/api.py" in content
    assert "app/routes/history.py" in content
    assert "_ioc_template_context()" in content
    assert "_history_ioc_template_context()" in content
    assert "_serialized_ioc_response_payload()" in content
    assert "code-path reasoning + focused regression proof" in content
    assert "python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py" in content
    assert "Preserve online-admission error visibility" in content
    assert "capture-command failure visibility" in content
    assert "secret redaction" in content
    assert "Keep S03's diagnostics sanitization caps behind the shared immutable policy object" in content
    assert "S03 diagnostics/redaction contract" in content
    assert "diagnostic export/sanitization" in content
    assert "app/diagnostics/policy.py" in content
    assert "app/diagnostics/assembler.py" in content
    assert "app/diagnostics/redaction.py" in content
    assert "app/diagnostics/sources.py" in content
    assert "T02 inspected the production modules and left behavior alone" in content
    assert "shipped as a centralization keep-decision, not rejected" in content
    assert "python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py" in content
    assert "diagnostic source status/error/omitted/truncated manifest states" in content
    assert "archive validation errors" in content
    assert "config read errors as secret-free metadata" in content
    assert "failed audit capture visibility" in content
    assert "exact-secret longest-first replacement" in content
    assert "no raw provider keys, bearer tokens, secrets" in content
    assert "`.gsd`/`.planning`/`.audits`/`.git` contents" in content
    assert "Keep large-result frontend rendering on the severity-change gate and defer virtualization" in content
    assert "S04 browser-visible deferment" in content
    assert "measures large-result render pressure at the severity-change gate" in content
    assert "240-card results fixture" in content
    assert "zero `.ioc-card` whole-grid scans, zero dashboard recounts, and zero sort calls" in content
    assert "exactly one document-level card scan" in content
    assert "Current evidence supports preserving the severity-change gate rather than promoting DOM virtualization" in content
    assert "`make verify-deep` for browser-visible/live-enrichment-visible proof" in content
    assert "Preserve filtering, sorting, copy/export, detail links, expansion state, live/history parity" in content
    assert "failure visibility through DOM state, mocked-online browser failures" in content
    assert "without logging secrets or provider payloads" in content
    assert "Defer frontend DOM virtualization" in content
    assert "virtualization remains deferred until measured browser-visible pressure justifies it" in content
    assert "virtualization shipped" not in content.lower()
    assert "virtualization is shipped" not in content.lower()
    assert "Leave provider concurrency/backoff semantics alone" in content
    assert "app/enrichment/retry_policy.py" in content
    assert "app/enrichment/lookup_execution.py::run_lookup_with_retries()" in content
    assert "app/enrichment/lookup_execution.py::run_attempt_with_semaphore()" in content
    assert "retry constants, 429/rate-limit classification, and exponential delay math" in content
    assert "test_orchestrator_delegates_retry_policy_helpers" in content
    assert "test_orchestrator_delegates_retry_execution_loop" in content
    assert "test_orchestrator_delegates_semaphore_attempt_boundary" in content
    assert "backoff sleeps outside semaphore-scoped lookup attempts" in content
    assert "embedding semaphore acquire/release mechanics in the orchestrator class" in content
    assert "keep retry policy constants/classification centralized" in content
    assert "Refresh S05's final closeout audit after every shipped, rejected, or deferred rewrite" in content
    assert "Final `make verify` remains the S05 closeout proof lane" in content
    assert "full app verification lane passes" in content
    assert "failure-visibility and redaction guardrails" in content
    assert "route/API responses for missing-provider and empty-path behavior" in content
    assert "diagnostic bundle manifest status/error/omitted/truncated metadata" in content
    assert "redaction metadata without raw secrets" in content
    assert "generated audit command-capture rows, including failed-capture visibility" in content
    assert "S02 shipped route helper centralization" in content
    assert "S03 shipped diagnostics policy centralization" in content
    assert "S04 rejected virtualization promotion" in content
    assert "make verify-fast" in content
    assert "make verify-deep" in content
    assert "make verify` plus refreshed generated M020 audit" in content
    assert "_Fill during the do now pass_" not in content
    assert "_Fill during the do next pass_" not in content
    assert "_Fill during the later pass_" not in content
    assert "_Fill during the leave alone pass_" not in content


def test_m020_template_and_default_output_are_milestone_local(tmp_path):
    audit = load_audit_module()
    template_document = audit.AuditDocument(
        milestone_id="M020",
        mode="template",
        repo_name="SentinelX",
        repo_root=tmp_path,
        output_path=tmp_path / "unused.md",
        generated_at="2026-01-01 00:00:00 UTC",
    )

    content = audit.render_document(template_document)

    assert ".gsd/milestones/M020/M020-AUDIT-TEMPLATE.md" in content
    assert ".gsd/milestones/M020/M020-AUDIT.md" in content
    assert "make audit-m020-template" in content
    assert "make audit-m020" in content
    assert "M017-AUDIT" not in content


def test_m020_failed_capture_is_visible_in_generated_artifact(tmp_path):
    output_path = tmp_path / "m020-audit.md"

    result = run_audit(
        "--milestone-id",
        "M020",
        "--mode",
        "baseline",
        "--output",
        str(output_path),
        "--capture-command",
        "bad::python3 -c 'import sys; print(\"m020 bad capture\"); sys.exit(9)'",
    )

    assert result.returncode == 0, result.stderr
    content = output_path.read_text(encoding="utf-8")
    assert "| bad |" in content
    assert "| 9 |" in content
    assert "m020 bad capture" in content
    assert "capture 'bad' failed with exit code 9" in result.stderr


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


def test_main_reports_failed_captures_without_list_comprehension() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "failed_captures = [" not in source
    assert "for capture in captures:" in source


def test_summarize_output_uses_shared_whitespace_collapse() -> None:
    audit = load_audit_module()

    class NoSplitText(str):
        def split(self, *_args, **_kwargs):
            raise AssertionError("summarize_output should not split command output lines")

    summary = audit.summarize_output(
        NoSplitText("  first\tline\n"),
        NoSplitText("  second\n\n third   line  "),
    )

    assert summary == "first line | second | third line"


def test_summary_truncation_trims_suffix_without_rstrip() -> None:
    audit = load_audit_module()

    class NoRstripText(str):
        def rstrip(self, *_args, **_kwargs):
            raise AssertionError("summary truncation should trim trailing whitespace by index")

    assert audit._rstrip_whitespace(NoRstripText("alpha  \t")) == "alpha"
    assert "rstrip" not in audit._rstrip_whitespace.__code__.co_names

    summary = audit.summarize_output("x" * 216 + "   " + "y" * 10, "")

    assert summary == ("x" * 216) + "..."
    assert len(summary) == 219


def test_runtime_provider_summary_rejects_missing_fields():
    audit = load_audit_module()

    with pytest.raises(ValueError, match="missing diagnostics fields"):
        audit.summarize_runtime_provider_diagnostics(
            {
                "dispatch_count": 1,
                "providers": {"CacheAlpha": {"dispatch_count": 1, "error_count": 0}},
            }
        )


def test_runtime_provider_missing_field_formatting_uses_short_paths():
    audit = load_audit_module()

    assert audit._format_runtime_fields(("dispatch_count",)) == "dispatch_count"
    assert audit._format_runtime_fields(("dispatch_count", "providers")) == "dispatch_count, providers"
    assert audit._format_runtime_fields(("dispatch_count", "providers", "diagnostics")) == (
        "dispatch_count, providers, diagnostics"
    )
    assert audit._format_runtime_fields((
        "dispatch_count",
        "providers",
        "diagnostics",
        "retry_count",
    )) == "dispatch_count, providers, diagnostics, retry_count"
    assert audit._missing_runtime_fields(("dispatch_count", "providers"), {"dispatch_count": 1}) == (
        "providers",
    )

    nested_code_names = {
        const.co_name
        for const in audit.summarize_runtime_provider_diagnostics.__code__.co_consts
        if hasattr(const, "co_name")
    }
    source = SCRIPT.read_text(encoding="utf-8")
    helper_source = source[
        source.index("def _missing_runtime_fields"):
        source.index("def summarize_runtime_provider_diagnostics")
    ]

    assert "<listcomp>" not in nested_code_names
    assert 'if field_count == 4:' in helper_source
    assert 'if field_count == 3:' in helper_source
    assert '", ".join(fields)' in helper_source
    assert "_missing_runtime_fields" in audit.summarize_runtime_provider_diagnostics.__code__.co_names
    assert "_format_runtime_fields" in audit.summarize_runtime_provider_diagnostics.__code__.co_names


def test_runtime_provider_mix_skips_items_view_and_single_provider_sort(monkeypatch):
    audit = load_audit_module()

    class NoItemsProviders(dict):
        def items(self):
            raise AssertionError("provider mix rendering should iterate provider keys directly")

    providers = NoItemsProviders({
        "CacheAlpha": {
            "dispatch_count": 2,
            "attempt_count": 2,
            "cache_hits": 1,
            "cache_misses": 1,
            "retry_count": 0,
            "rate_limit_retry_count": 0,
            "error_count": 0,
            "latency_total_seconds": 0.1,
            "latency_max_seconds": 0.1,
        }
    })

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("single-provider mix rendering should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    assert audit._render_runtime_provider_mix(providers) == "CacheAlpha:2d/0e"
    assert "items" not in audit._render_runtime_provider_mix.__code__.co_names


def test_runtime_provider_mix_orders_short_provider_sets_without_sort(monkeypatch):
    audit = load_audit_module()

    providers = {
        "RateLimitBeta": {
            "dispatch_count": 2,
            "attempt_count": 3,
            "cache_hits": 0,
            "cache_misses": 2,
            "retry_count": 1,
            "rate_limit_retry_count": 1,
            "error_count": 1,
            "latency_total_seconds": 0.2,
            "latency_max_seconds": 0.2,
        },
        "CacheAlpha": {
            "dispatch_count": 2,
            "attempt_count": 2,
            "cache_hits": 1,
            "cache_misses": 1,
            "retry_count": 0,
            "rate_limit_retry_count": 0,
            "error_count": 0,
            "latency_total_seconds": 0.1,
            "latency_max_seconds": 0.1,
        },
        "MiddleProvider": {
            "dispatch_count": 1,
            "attempt_count": 1,
            "cache_hits": 0,
            "cache_misses": 1,
            "retry_count": 0,
            "rate_limit_retry_count": 0,
            "error_count": 0,
            "latency_total_seconds": 0.05,
            "latency_max_seconds": 0.05,
        },
        "ArchiveGamma": {
            "dispatch_count": 4,
            "attempt_count": 4,
            "cache_hits": 2,
            "cache_misses": 2,
            "retry_count": 0,
            "rate_limit_retry_count": 0,
            "error_count": 0,
            "latency_total_seconds": 0.15,
            "latency_max_seconds": 0.05,
        },
    }

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("short provider mix rendering should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    assert audit._render_runtime_provider_mix(providers) == (
        "ArchiveGamma:4d/0e, CacheAlpha:2d/0e, MiddleProvider:1d/0e, RateLimitBeta:2d/1e"
    )
    assert audit._ordered_provider_names(providers) == (
        "ArchiveGamma",
        "CacheAlpha",
        "MiddleProvider",
        "RateLimitBeta",
    )
    source = SCRIPT.read_text(encoding="utf-8")
    mix_source = source[
        source.index("def _render_runtime_provider_mix"):
        source.index("def _runtime_provider_mix_entry")
    ]
    assert "_runtime_provider_mix_entry(first, providers[first])" in mix_source
    assert "_runtime_provider_mix_entry(second, providers[second])" in mix_source
    assert "_runtime_provider_mix_entry(third, providers[third])" in mix_source
    assert "_runtime_provider_mix_entry(fourth, providers[fourth])" in mix_source
    assert "entries.append" in mix_source


def test_ordered_strings_handles_four_values_without_sort(monkeypatch):
    audit = load_audit_module()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("short string ordering should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    assert audit._ordered_strings({"delta", "alpha", "charlie", "bravo"}) == (
        "alpha",
        "bravo",
        "charlie",
        "delta",
    )
    assert audit._ordered_four_strings("delta", "alpha", "charlie", "bravo") == (
        "alpha",
        "bravo",
        "charlie",
        "delta",
    )
    assert audit._ordered_three_strings("delta", "alpha", "charlie") == (
        "alpha",
        "charlie",
        "delta",
    )
    assert "_ordered_three_strings" in audit._ordered_provider_names.__code__.co_names
    assert "_ordered_three_strings" in audit._ordered_strings.__code__.co_names
    assert "_ordered_four_strings" in audit._ordered_provider_names.__code__.co_names
    assert "_ordered_four_strings" in audit._ordered_strings.__code__.co_names


def test_runtime_provider_measurement_fixtures_copy_directly() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "return dict(row)" not in source
    assert "{**payload," not in source
    assert "list(result_list)" not in source
    assert "outcomes.items()" not in source


def test_pipeline_duplicate_measurement_accumulates_values_directly(monkeypatch) -> None:
    audit = load_audit_module()
    import app.pipeline.extractor  # noqa: F401

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("single duplicate-candidate output value should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    summary = audit.measure_pipeline_duplicate_candidates()
    nested_code_names = {
        const.co_name
        for const in audit.measure_pipeline_duplicate_candidates.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert "7 raw URL variants normalize to 1 IOC value" in summary
    assert "classify calls=1" in summary
    assert "<setcomp>" not in nested_code_names
    assert "<listcomp>" not in nested_code_names


def test_status_snapshot_measurement_seeds_results_directly() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "list(range(retained_results))" not in source


def test_ranked_finding_renderers_share_direct_bucket_filter() -> None:
    audit = load_audit_module()
    nested_code_names = {
        const.co_name
        for function in (audit.render_baseline_ranked_findings, audit.render_m017_ranked_findings)
        for const in function.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert audit._findings_for_bucket(audit.BASELINE_FINDINGS, "leave alone")
    assert audit._findings_for_bucket(audit.M017_FINDINGS, "do now")
    assert "<listcomp>" not in nested_code_names
    assert "_findings_for_bucket" in audit.render_baseline_ranked_findings.__code__.co_names
    assert "_findings_for_bucket" in audit.render_m017_ranked_findings.__code__.co_names


def test_findings_table_renders_rows_without_field_list_allocation() -> None:
    audit = load_audit_module()
    source = SCRIPT.read_text(encoding="utf-8")
    function_source = source[
        source.index("def render_findings_table") : source.index("def render_baseline_ranked_findings")
    ]
    nested_code_names = {
        const.co_name
        for const in audit.render_findings_table.__code__.co_consts
        if hasattr(const, "co_name")
    }

    table = audit.render_findings_table([audit.M017_FINDINGS[0]])

    assert "| Finding | Seam | Evidence kind | Evidence summary |" in table
    assert audit.M017_FINDINGS[0].finding in table
    assert "<listcomp>" not in nested_code_names
    assert '" | ".join(' not in function_source
    assert "[\n                    finding.finding" not in function_source


def test_audit_renderers_trim_joined_lines_without_direct_rstrip() -> None:
    audit = load_audit_module()
    source = SCRIPT.read_text(encoding="utf-8")

    assert audit._join_lines_trimmed(["alpha", "", ""]) == "alpha"
    assert ".rstrip()" not in source
    assert "_join_lines_trimmed" in audit.render_seams_section.__code__.co_names
    assert "_join_lines_trimmed" in audit.render_baseline_ranked_findings.__code__.co_names
    assert "_join_lines_trimmed" in audit.render_baseline_seam_notes.__code__.co_names
    assert "_join_lines_trimmed" in audit.render_m017_ranked_findings.__code__.co_names
    assert "_join_lines_trimmed" in audit.render_document.__code__.co_names


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
