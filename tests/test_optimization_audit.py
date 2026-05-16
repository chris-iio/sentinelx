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
    assert "get_incremental_status(since=4990)" in content
    assert "tail rows plus aligned `cached_markers`" in content
    assert "test_get_status_snapshot_copies_results_directly" in content
    assert "full-status result isolation" in content
    assert "test_get_incremental_status_nonnegative_since_does_not_slice_results" in content
    assert "test_get_incremental_status_copies_tail_without_list_constructor" in content
    assert "test_get_incremental_status_preserves_negative_since_behavior" in content
    assert "preserving Python negative-slice compatibility" in content
    assert "constructor-copying cached markers or incremental result tails" in content
    assert "test_get_incremental_status_returns_empty_tail_beyond_retained_length" in content
    assert "test_get_incremental_status_builds_scalar_fields_without_items_scan" in content
    assert "Scalar status fields are now copied directly by known public key" in content
    assert "itertools.islice()" in content
    assert "incremental status snapshots now return empty out-of-range cursor tails before walking retained results" in content
    assert "test_cached_markers_snapshot_copies_directly" in content
    assert "constructor-copying cached markers" in content
    assert "status.get('cached_markers')` once per payload" in content
    assert "test_enrichment_status_reads_cached_markers_once_per_payload" in content
    assert "_get_enrichment_status()` against list-comprehension frames" in content
    assert "_build_status_payload()" in content
    assert "test_status_payload_uses_explicit_next_since_without_measuring_results" in content
    assert "eagerly measuring retained results when an explicit cursor exists" in content
    assert "_STATUS_NOT_FOUND_REASONS" in content
    assert "test_enrichment_status_not_found_reasons_use_static_membership_set" in content
    assert "terminal-not-found reason sets per response" in content
    assert "test_serialize_result_skips_empty_cached_marker_map" in content
    assert "test_save_serializes_results_and_iocs_with_direct_loops" in content
    assert "Background history-save serialization now accumulates result and IOC payloads with direct loops" in content
    assert "test_history_save_diagnostics_falls_back_to_safe_defaults" in content
    assert "test_history_save_diagnostics_presence_checks_avoid_timestamp_strip" in content
    assert "test_history_save_diagnostics_error_summary_strips_once" in content
    assert "test_orchestration_status_string_coercion_strips_once" in content
    assert "fixed diagnostic/status field groups and recordable outcome sets now live as module constants" in content
    assert "constructor-copying history-save diagnostic defaults/snapshots" in content
    assert "repeatedly stripping diagnostic status strings" in content
    assert "rebuilding diagnostic/status field tuples" in content
    assert "test_orchestration_diagnostics_evicted_job_copies_terminal_snapshot_directly" in content
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
    assert "_provider_counts_json()" in content
    assert "ProviderRegistry.registered_count()" in content
    assert "test_provider_counts_metadata_uses_direct_count_path" in content
    assert "test_provider_coverage_reuses_configured_provider_list" in content
    assert "test_registered_count_does_not_allocate_provider_list" in content
    assert "direct accumulator and `registry.provider_count_for_type()`" in content
    assert "registered-provider list copies for coverage counts" in content
    assert "dict-comprehension frame" in content
    assert "browser-route provider-count metadata and coverage counts now use registry direct count paths" in content
    assert "Keep Online fanout admission diagnostics on the direct count path." in content
    assert "_online_fanout_diagnostics()" in content
    assert "_online_limits_from_config()" in content
    assert "test_online_fanout_diagnostics_uses_direct_count_path" in content
    assert "test_analyze_online_uses_shared_limit_config_helper" in content
    assert "test_online_uses_shared_limit_config_helper" in content
    assert "Online fanout admission diagnostics now use cached direct provider counts" in content
    assert "duplicated online-limit config parsing" in content
    assert "Keep browser-route enrichable progress totals on cached provider counts by IOC type." in content
    assert "_enrichable_count()" in content
    assert "test_enrichable_count_caches_provider_counts_by_ioc_type" in content
    assert "test_analyze_online_reuses_fanout_dispatch_count_for_progress_total" in content
    assert "browser-route enrichable progress totals now reuse admission fanout counts" in content
    assert "Keep online route configured-provider reads single-use across admission, coverage, and launch." in content
    assert "_provider_coverage()" in content
    assert "_setup_orchestrator()" in content
    assert "test_provider_coverage_reuses_configured_provider_list" in content
    assert "test_analyze_online_no_iocs_skips_enrichment_setup" in content
    assert "test_online_no_iocs_skips_enrichment_setup" in content
    assert "online routes now reuse the configured-provider list across admission" in content
    assert "skip provider setup entirely for zero-IOC submissions" in content
    assert "Keep API health registry detail on direct registry count paths." in content
    assert "_registry_health_detail()" in content
    assert "ProviderRegistry.configured_count()" in content
    assert "test_health_touches_only_aggregate_provider_configuration" in content
    assert "test_configured_count_does_not_allocate_provider_list" in content
    assert "registered or configured provider lists" in content
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
    assert "test_groups_serialized_iocs_in_one_pass" in content
    assert "test_online_no_providers_skips_ioc_serialization" in content
    assert "test_api_analyze_uses_shared_text_presence_check" in content
    assert "API analyze responses now serialize and group each IOC in one pass only after online admission checks pass" in content
    assert "Keep browser analyze IOC grouping on a route-local pass." in content
    assert "_group_iocs_for_template()" in content
    assert "test_analyze_groups_template_iocs_without_group_by_type" in content
    assert "test_analyze_online_without_api_key_skips_template_grouping" in content
    assert "test_analyze_uses_shared_text_presence_check" in content
    assert "browser analyze responses now group template IOCs directly in the route only after online missing-provider redirects are ruled out" in content
    assert "request text presence checks" in content
    assert "Keep history reload IOC reconstruction, grouping, and empty replay serialization lean." in content
    assert "_group_history_iocs()" in content
    assert "test_history_groups_iocs_while_rebuilding_models" in content
    assert "test_empty_history_skips_ioc_grouping" in content
    assert "empty history reloads skip the grouping helper entirely" in content
    assert "_history_results_json()" in content
    assert "test_empty_history_results_skip_json_dumps" in content
    assert "shared empty provider-counts JSON literal" in content
    assert "ad hoc empty provider-count JSON literals" in content
    assert "app/static/src/ts/modules/history.test.ts" in content
    assert "empty replay JSON parsing" in content
    assert "`#enrich-progress`, `#enrich-progress-text`, `#export-btn`, and `#export-dropdown` once" in content
    assert "parsed replay verifies each history completion/export ID is looked up once" in content
    assert "repeated completion/export ID lookups on history reload" in content
    assert "history reload now rebuilds and groups persisted IOC models in one pass, skips empty-history grouping, and returns the empty replay JSON literal" in content
    assert "Keep IOC detail valid-type checks on a precomputed set." in content
    assert "_VALID_IOC_TYPES" in content
    assert "test_valid_ioc_types_are_precomputed" in content
    assert "test_detail_page_empty_cache" in content
    assert "literal empty graph payloads" in content
    assert "discarded empty-cache graph node allocation" in content
    assert "valid-type generator/comprehension frames" in content
    assert "IOC detail routes now use a precomputed valid-type set" in content
    assert "Keep orchestration diagnostic export coercion on bounded iteration." in content
    assert "_coerce_orchestration_diagnostics_for_export()" in content
    assert "itertools.islice()" in content
    assert "test_orchestration_diagnostics_export_coercion_uses_bounded_iteration" in content
    assert "test_orchestration_diagnostics_export_coercion_does_not_slice_lists" in content
    assert "orchestration diagnostic export coercion now applies top-level, nested dict, and list caps with bounded key/list iteration" in content
    assert "orchestration diagnostic mapping items-view allocation" in content
    assert "Keep diagnostic source sanitization on bounded mapping and sequence iteration." in content
    assert "_safe_jsonish()" in content
    assert "_safe_mapping()" in content
    assert "test_safe_mapping_uses_bounded_iteration_for_nested_mappings" in content
    assert "test_safe_jsonish_uses_direct_recursive_loops" in content
    assert "mapping items-view allocation" in content
    assert "recursive comprehension-frame allocation" in content
    assert "diagnostic source sanitization now applies mapping and sequence caps with bounded iteration" in content
    assert "Keep recent-history diagnostic payloads on bounded iteration." in content
    assert "_recent_history_payload()" in content
    assert "test_recent_history_payload_uses_bounded_iteration_not_slice" in content
    assert "test_recent_history_payload_accumulates_without_list_comprehension_frame" in content
    assert "comprehension-frame allocation" in content
    assert "recent-history diagnostic payloads now use bounded iteration over returned rows" in content
    assert "Keep diagnostic manifest duplicate-source validation single-pass." in content
    assert "DiagnosticManifest.__post_init__()" in content
    assert "test_manifest_duplicate_source_validation_stops_at_first_duplicate" in content
    assert "diagnostic manifest deterministic serialization" in content
    assert "Keep diagnostic safe-error summary whitespace normalization on compiled regex." in content
    assert "_normalize_error_summary()" in content
    assert "test_safe_error_summary_normalizes_whitespace_without_split_list" in content
    assert "test_source_record_text_normalization_uses_shared_helper" in content
    assert "duplicate local stripped-text helper logic" in content
    assert "diagnostic safe-error summary normalization now uses a compiled whitespace regex" in content
    assert "Keep diagnostic manifest aggregate serialization single-pass." in content
    assert "DiagnosticManifest.to_dict()" in content
    assert "test_manifest_reuses_construction_time_sorted_sources" in content
    assert "avoiding repeated sorting" in content
    assert "test_manifest_construction_skips_sort_for_zero_or_one_source" in content
    assert "test_manifest_serialization_computes_counts_in_one_source_pass" in content
    assert "test_source_record_serializes_redaction_labels_without_list_constructor" in content
    assert "source-record label serialization against `list(...)` constructor calls" in content
    assert "source-record label constructor copies" in content
    assert "test_redaction_label_normalization_uses_direct_accumulation" in content
    assert "test_redaction_label_normalization_skips_sort_for_zero_or_one_label" in content
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
    assert "test_single_source_bundle_skips_sorting" in content
    assert "unnecessary single-source/payload sorting" in content
    assert "test_bundle_summary_does_not_serialize_sources" in content
    assert "summary-time source serialization" in content
    assert "test_json_safe_uses_direct_recursive_loops" in content
    assert "test_diagnostic_source_text_normalization_uses_shared_helper" in content
    assert "recursive mapping items-view allocation" in content
    assert "recursive comprehension frames during payload encoding" in content
    assert "diagnostic bundle deterministic archive ordering" in content
    assert "Keep diagnostic archive path validation on single-pass segment scanning." in content
    assert "_iter_archive_path_segments()" in content
    assert "test_archive_path_validation_scans_segments_without_split_list" in content
    assert "diagnostic archive path validation now scans path segments once" in content
    assert "Keep diagnostic exact-secret redaction on preordered candidates." in content
    assert "_apply_exact_secret_redaction()" in content
    assert "test_exact_secret_redaction_reuses_preordered_candidates" in content
    assert "test_redaction_metadata_reuses_sorted_label_snapshot" in content
    assert "test_configured_secret_collection_avoids_item_pairs_and_generator_frames" in content
    assert "test_configured_secret_collection_strips_each_secret_once" in content
    assert "test_configured_secret_collection_skips_sort_for_single_provider" in content
    assert "repeated configured-secret stripping" in content
    assert "unnecessary single-item provider/label sorting" in content
    assert "provider item-pair sorting" in content
    assert "secret-label generator frames" in content
    assert "test_payload_redaction_uses_direct_recursive_loops" in content
    assert "recursive payload items-view/list-comprehension allocation" in content
    assert "test_configured_secret_inventory_deduplicates_provider_labels_directly" in content
    assert "provider label list-to-set copies" in content
    assert "unnecessary metadata label sorting" in content
    assert "test_redaction_metadata_skips_sort_for_zero_or_one_label" in content
    assert "skips `sorted()` entirely for empty or single-label metadata" in content
    assert "unnecessary metadata label sorting" in content
    assert "test_label_part_normalization_uses_compiled_regex" in content
    assert "test_config_secret_inventory_payload_accumulates_labels_without_list_constructor" in content
    assert "label `list(...)` constructor calls" in content
    assert "diagnostic-source label constructor copies" in content
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
    assert "_EMPTY_JSON_OBJECT" in content
    assert "CacheStore.put()" in content
    assert "test_empty_payload_skips_json_encoding" in content
    assert "CacheStore.get()" in content
    assert "get_all_for_ioc()" in content
    assert "test_empty_payload_skips_json_decoding" in content
    assert "test_empty_payload_uses_shared_json_literal_constant" in content
    assert "empty cache read/write payloads now use JSON literals" in content
    assert "unnecessary JSON encoder and decoder calls for empty cache payloads" in content
    assert "duplicated JSON literal strings" in content
    assert "Keep cache/history SQLite PRAGMA setup behind the shared `app.sqlite.configure_connection()` helper." in content
    assert "tests/test_sqlite.py" in content
    assert "removing duplicated store initialization code" in content
    assert "Keep recent-history summaries on the SQL-side input preview projection." in content
    assert "substr(input_text, 1, 120)" in content
    assert "test_truncates_input_text" in content
    assert "test_list_recent_accumulates_summaries_without_list_comprehension" in content
    assert "guards `list_recent()` against `<listcomp>` bytecode" in content
    assert "comprehension-frame allocation around bounded summary rows" in content
    assert "full history reload preserves the saved input" in content
    assert "Keep empty history save/load payloads on JSON literals." in content
    assert "_EMPTY_JSON_ARRAY" in content
    assert "HistoryStore.save_analysis()" in content
    assert "test_empty_payloads_skip_json_encoding" in content
    assert "HistoryStore.load_analysis()" in content
    assert "test_empty_payloads_skip_json_decoding" in content
    assert "test_empty_payloads_use_shared_json_literal_constant" in content
    assert "empty history save/load payloads now use JSON literals" in content
    assert "unnecessary JSON encoder and decoder calls for empty saved payloads" in content
    assert "duplicated JSON literal strings" in content
    assert "Keep SSH auth.log parsing on streaming lines, direct BSD timestamps, and cached source classification." in content
    assert "app/ssh/parser.py::_iter_lines()" in content
    assert "test_text_stream_is_not_read_all_at_once" in content
    assert "test_bsd_timestamp_parsing_does_not_use_strptime" in content
    assert "test_repeated_source_classification_is_cached" in content
    assert "caches repeated source classification" in content
    assert "Keep history top-verdict computation on the malicious short-circuit path." in content
    assert "_MAX_VERDICT" in content
    assert "_FALLBACK_VERDICT" in content
    assert "test_malicious_verdict_short_circuits_scan" in content
    assert "test_top_verdict_terminal_constants_are_precomputed" in content
    assert "history top-verdict computation now short-circuits" in content
    assert "duplicated terminal verdict literals" in content
    assert "Keep history verdict priority on a precomputed map." in content
    assert "_VERDICT_PRIORITY" in content
    assert "test_priority_map_is_precomputed" in content
    assert "repeated priority-map allocation" in content
    assert "Keep `ProviderRegistry` filters on direct provider scans." in content
    assert "test_all_accumulates_without_values_view" in content
    assert "unnecessary values-view" in content
    assert "test_list_filters_do_not_allocate_comprehension_frames" in content
    assert "test_list_filters_scan_without_values_view" in content
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
    assert "_select_best_record()" in content
    assert "app/enrichment/adapters/threatfox.py::_threatfox_result()" in content
    assert "test_best_record_selection_short_circuits_on_perfect_confidence" in content
    assert "tests/test_threatfox.py::TestEdgeCases::test_result_helper_preserves_provider_envelope" in content
    assert "ThreatFox result construction now uses one provider envelope helper" in content
    assert "Keep ASN TXT parsing on first-record and direct field extraction." in content
    assert "CymruASNAdapter.lookup()" in content
    assert "test_txt_answer_uses_first_record_without_materializing_all_answers" in content
    assert "test_single_chunk_txt_answer_skips_join_iteration" in content
    assert "test_multi_chunk_txt_answer_still_concatenates_segments" in content
    assert "test_txt_parse_does_not_allocate_split_parts" in content
    assert "test_no_data_result_helper_preserves_informational_shape" in content
    assert "single-chunk TXT join iteration" in content
    assert "duplicated no-data result construction" in content
    assert "no-HTTP/no-requests boundaries" in content
    assert "Keep DNS record extraction on table-driven dispatch." in content
    assert "DnsAdapter.lookup()" in content
    assert "app/enrichment/adapters/dns_lookup.py::_dns_result()" in content
    assert "test_lookup_uses_record_table_extractors" in content
    assert "test_single_chunk_txt_record_skips_join_iteration" in content
    assert "test_record_extractors_do_not_allocate_list_comprehension_frames" in content
    assert "unnecessary single-chunk TXT join iteration" in content
    assert "list-comprehension extractor frames" in content
    assert "tests/test_dns_lookup.py::TestSuccessfulLookup::test_result_helper_preserves_provider_envelope" in content
    assert "DNS result construction now uses one informational provider envelope helper" in content
    assert "Keep VirusTotal engine total computation in the stats scan." in content
    assert "virustotal.py::_parse_response()" in content
    assert "VTAdapter.supported_types" in content
    assert "app/enrichment/adapters/virustotal.py::_virustotal_result()" in content
    assert "test_total_engine_count_does_not_use_sum_helper" in content
    assert "test_engine_status_exclusions_use_static_frozenset" in content
    assert "test_top_detections_do_not_allocate_values_view" in content
    assert "stats items-view allocation" in content
    assert "per-parse excluded-status set construction" in content
    assert "analysis-result values-view allocation" in content
    assert "tests/test_vt_adapter.py::test_supported_types_derive_from_endpoint_map" in content
    assert "tests/test_vt_adapter.py::TestLookupSuccess::test_result_helper_preserves_provider_envelope" in content
    assert "VirusTotal stats parsing still computes engine totals in one scan" in content
    assert "top detections, reputation" in content
    assert "Keep ThreatMiner capped result extraction bounded." in content
    assert "app/enrichment/adapters/threatminer.py" in content
    assert "test_ip_lookup_passive_dns_stops_at_cap" in content
    assert "test_zero_cap_passive_dns_skips_result_iteration" in content
    assert "test_zero_cap_samples_skip_result_iteration" in content
    assert "zero-cap result iteration" in content
    assert "test_dict_sample_rows_do_not_allocate_values_view" in content
    assert "dict values-view allocation" in content
    assert "test_no_data_result_helper_preserves_informational_shape" in content
    assert "full oversized result scans" in content
    assert "duplicated no-data result construction" in content
    assert "Keep crt.sh certificate parsing on one body scan." in content
    assert "app/enrichment/adapters/crtsh.py::_parse_response()" in content
    assert "app/enrichment/adapters/crtsh.py::_crtsh_result()" in content
    assert "test_date_range_and_subdomains_computed_in_one_body_scan" in content
    assert "test_name_value_parsing_does_not_allocate_split_list" in content
    assert "test_empty_or_single_subdomain_sets_skip_sorting" in content
    assert "test_subdomain_cap_avoids_full_sorted_list" in content
    assert "test_result_helper_preserves_provider_envelope" in content
    assert "crt.sh certificate parsing still uses one body scan" in content
    assert "crt.sh subdomain selection now skips sorting empty or single-subdomain sets" in content
    assert "wildcard stripping" in content
    assert "per-certificate SAN split-list allocation" in content
    assert "unnecessary empty/single subdomain sorting" in content
    assert "full oversized subdomain sorting" in content
    assert "Keep Shodan malicious-tag detection on a direct count." in content
    assert "app/enrichment/adapters/shodan.py::_parse_response()" in content
    assert "test_malicious_tag_count_preserves_duplicate_bad_tags" in content
    assert "test_result_helper_preserves_provider_envelope" in content
    assert "Shodan result construction now uses one provider envelope helper" in content
    assert "intermediate bad-tag list allocation" in content
    assert "Keep EmailRep malicious verdict selection on the risk-flag scan." in content
    assert "app/enrichment/adapters/emailrep.py::_risk_flags()" in content
    assert "app/enrichment/adapters/emailrep.py::_emailrep_result()" in content
    assert "test_verdict_uses_risk_flag_scan_without_second_malicious_pass" in content
    assert "test_verdict_membership_tables_are_static_frozensets" in content
    assert "tests/test_emailrep.py::TestEmailRepLookup::test_result_helper_preserves_provider_envelope" in content
    assert "EmailRep result construction now uses one provider envelope helper" in content
    assert "per-parse verdict membership set construction" in content
    assert "Keep AbuseIPDB parsed result construction behind one provider envelope helper." in content
    assert "app/enrichment/adapters/abuseipdb.py::_abuseipdb_result()" in content
    assert "tests/test_abuseipdb.py::TestAbuseIPDBLookup::test_result_helper_preserves_provider_envelope" in content
    assert "AbuseIPDB result construction now uses one provider envelope helper" in content
    assert "Keep IP Context geo and ASN/ISP formatting on direct string construction." in content
    assert "app/enrichment/adapters/ip_api.py::_parse_response()" in content
    assert "test_geo_format_exact_full_context" in content
    assert "test_org_parsing_does_not_allocate_split_parts" in content
    assert "test_no_data_result_helper_preserves_informational_shape" in content
    assert "temporary geo-part and ASN/ISP split-list allocation" in content
    assert "duplicated no-data result construction" in content
    assert "Keep WHOIS name-server normalization on list reuse." in content
    assert "app/enrichment/adapters/whois_lookup.py::_normalise_name_servers()" in content
    assert "app/enrichment/adapters/whois_lookup.py::_whois_result()" in content
    assert "test_name_server_lists_are_reused_without_copying" in content
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
    assert "skips the no-op `Session.headers.update({})`" in content
    assert "test_default_auth_headers_skip_empty_session_update" in content
    assert "no-op empty header updates" in content
    assert "HTTP adapters now cache allowed-host membership as a frozenset" in content
    assert "Keep route-mapped adapter support declarations derived from endpoint maps." in content
    assert "test_supported_types_derive_from_hash_route_map" in content
    assert "app/enrichment/adapters/hashlookup.py::_hashlookup_result()" in content
    assert "tests/test_hashlookup.py::TestLookupFound::test_result_helper_preserves_provider_envelope" in content
    assert "test_supported_types_derive_from_otx_route_map" in content
    assert "test_supported_types_derive_from_endpoint_map" in content
    assert "app/enrichment/adapters/otx.py::_otx_result()" in content
    assert "tests/test_otx.py::TestOTXLookup::test_result_helper_preserves_provider_envelope" in content
    assert "app/enrichment/adapters/urlhaus.py::_urlhaus_result()" in content
    assert "tests/test_urlhaus.py::TestURLhausLookup::test_result_helper_preserves_provider_envelope" in content
    assert "route-mapped HTTP adapters now derive supported IOC types from endpoint maps" in content
    assert "Hashlookup/OTX/URLhaus result construction now uses provider envelope helpers" in content
    assert "Keep MalwareBazaar result construction behind one provider envelope helper." in content
    assert "app/enrichment/adapters/malwarebazaar.py::_malwarebazaar_result()" in content
    assert "test_result_helper_preserves_provider_envelope" in content
    assert "MalwareBazaar result construction now uses one provider envelope helper" in content
    assert "Keep GreyNoise result construction behind one provider envelope helper." in content
    assert "app/enrichment/adapters/greynoise.py::_greynoise_result()" in content
    assert "GreyNoise result construction now uses one provider envelope helper" in content
    assert "Keep ConfigStore read-after-write on the cached parser path." in content
    assert "app/enrichment/config_store.py::_save_config()" in content
    assert "test_save_keeps_written_config_cached" in content
    assert "test_all_provider_keys_accumulates_directly_from_section" in content
    assert "test_provider_key_get_and_set_share_option_normalization" in content
    assert "provider-section constructor copies" in content
    assert "duplicated provider option-name normalization" in content
    assert "immediate read-after-write paths do not reparse disk" in content
    assert "Keep registry provider-key loading on one config map read." in content
    assert "app/enrichment/setup.py::build_registry()" in content
    assert "_register_keyed_provider()" in content
    assert "_register_zero_auth_provider()" in content
    assert "test_config_store_all_provider_keys_called_once_for_key_providers" in content
    assert "test_key_required_providers_share_registration_helper" in content
    assert "test_zero_auth_providers_share_registration_helper" in content
    assert "all 16 registered providers" in content
    assert "duplicated keyed-provider construction paths" in content
    assert "duplicated zero-auth construction paths" in content
    assert "Keep settings provider-key display on one config map read." in content
    assert "app/routes/settings.py::settings_get()" in content
    assert "app/routes/_helpers.py::_mask_key()" in content
    assert "test_get_settings_reads_provider_key_map_once" in content
    assert "test_mask_key_measures_configured_key_once" in content
    assert "masked key display" in content
    assert "repeated configured-key length work" in content
    assert "Keep settings provider validation on a precomputed ID set." in content
    assert "app/routes/settings.py::_VALID_PROVIDER_IDS" in content
    assert "direct helper loop" in content
    assert "test_save_provider_validation_uses_precomputed_id_set" in content
    assert "test_settings_post_and_cache_ttl_share_form_normalization" in content
    assert "generator/set-comprehension frames" in content
    assert "provider-id set construction" in content
    assert "duplicated form-value normalization" in content
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
    assert "S01 produces this generated audit artifact" in content
    assert "S02 consumed the highest-confidence route-helper candidate" in content
    assert "S05 refreshes final shipped/rejected outcomes" in content
    assert "### do now" in content
    assert "### do next" in content
    assert "### later" in content
    assert "### leave alone" in content
    assert "Keep S02's duplicate route IOC grouping rewrite on the shared route helper seam" in content
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
    assert "Defer frontend DOM virtualization" in content
    assert "Leave provider concurrency/backoff semantics alone" in content
    assert "make verify-fast" in content
    assert "make verify-deep" in content
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


def test_runtime_provider_mix_orders_two_providers_without_sort(monkeypatch):
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
    }

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("two-provider mix rendering should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    assert audit._render_runtime_provider_mix(providers) == "CacheAlpha:2d/0e, RateLimitBeta:2d/1e"
    source = SCRIPT.read_text(encoding="utf-8")
    mix_source = source[
        source.index("def _render_runtime_provider_mix"):
        source.index("def _runtime_provider_mix_entry")
    ]
    assert "_runtime_provider_mix_entry(first, providers[first])" in mix_source
    assert "_runtime_provider_mix_entry(second, providers[second])" in mix_source
    assert "entries.append" in mix_source


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
