"""Contract tests for shared UTC helper usage at integration boundaries."""
from __future__ import annotations

from app.diagnostics import sources as diagnostic_sources
from app.routes import _helpers as route_helpers
from app.routes import diagnostics as diagnostics_route
from tests.test_dev_server import load_dev_server_module
from tests.test_optimization_audit import load_audit_module
from tests.test_runtime_state_repair import load_repair_module


def test_diagnostic_sources_use_shared_utc_iso_helper() -> None:
    assert "utcnow_iso" in diagnostic_sources._utcnow_iso.__code__.co_names


def test_route_helpers_use_shared_utc_iso_helper() -> None:
    assert "utcnow_iso" in route_helpers._utcnow_iso.__code__.co_names


def test_diagnostic_route_uses_shared_utc_helpers() -> None:
    assert "utc_now" in diagnostics_route._utcnow.__code__.co_names
    assert "utc_iso" in diagnostics_route._utc_iso.__code__.co_names


def test_dev_server_uses_shared_utc_helpers() -> None:
    dev_server = load_dev_server_module()

    assert "utc_iso_seconds" in dev_server.utc_now.__code__.co_names
    assert "utc_timestamp_slug" in dev_server.utc_now_slug.__code__.co_names
    assert "utc_datetime_now" in dev_server._started_recently.__code__.co_names


def test_runtime_state_repair_uses_shared_utc_slug_helper() -> None:
    repair = load_repair_module()

    assert "utc_timestamp_slug" in repair.current_quarantine_stamp.__code__.co_names


def test_optimization_audit_uses_shared_utc_helpers() -> None:
    audit = load_audit_module()

    assert "utc_now" in audit.run_capture_command.__code__.co_names
    assert "utc_now" in audit.run_internal_capture.__code__.co_names
    assert "utc_display_seconds" in audit.main.__code__.co_names


def test_route_helpers_use_shared_bounded_text_helper() -> None:
    from app.routes import _helpers

    assert (
        "stripped_bounded_non_whitespace"
        in _helpers._coerce_history_save_diagnostics.__code__.co_names
    )
    assert (
        "stripped_bounded_non_whitespace"
        in _helpers._coerce_orchestration_status_for_diagnostics.__code__.co_names
    )


def test_diagnostics_and_audit_use_shared_whitespace_collapse() -> None:
    from app.diagnostics import contract

    audit = load_audit_module()

    assert "collapse_whitespace" in contract._normalize_error_summary.__code__.co_names
    assert "collapse_whitespace" in audit.summarize_output.__code__.co_names


def test_byte_decoders_use_shared_utf8_replace_helper() -> None:
    from app.diagnostics import assembler
    from app.enrichment.adapters import asn_cymru, dns_lookup
    from app.ssh import parser

    assert "decode_utf8_replace" in assembler._redact_and_encode_payload.__code__.co_names
    assert "_decode_txt_record" in dns_lookup._extract_txt_records.__code__.co_names
    assert "decode_utf8_replace" in dns_lookup._decode_txt_record.__code__.co_names
    assert "decode_utf8_replace" in asn_cymru._decode_txt_strings.__code__.co_names
    assert "decode_utf8_replace" in parser._iter_lines.__code__.co_names


def test_diagnostic_assembler_uses_manifest_byte_serializer() -> None:
    from app.diagnostics import assembler

    assert "manifest_to_json_bytes" in assembler.assemble_diagnostic_bundle.__code__.co_names


def test_empty_json_literals_are_shared_across_runtime_modules() -> None:
    from app.cache import store as cache_store
    from app.enrichment import history_store
    from app.routes import history as history_route
    from app.json_utils import EMPTY_JSON_ARRAY, EMPTY_JSON_OBJECT

    assert cache_store._EMPTY_JSON_OBJECT is EMPTY_JSON_OBJECT
    assert history_store._EMPTY_JSON_ARRAY is EMPTY_JSON_ARRAY
    assert history_route._EMPTY_JSON_ARRAY is EMPTY_JSON_ARRAY
    assert history_route._EMPTY_JSON_OBJECT is EMPTY_JSON_OBJECT


def test_empty_json_helpers_are_shared_across_runtime_modules() -> None:
    from app.cache import store as cache_store
    from app.enrichment import history_store
    from app.routes import history as history_route

    assert "encode_json_object" in cache_store._encode_result_json.__code__.co_names
    assert "decode_json_object" in cache_store._decode_result_json.__code__.co_names
    assert "encode_json_array" in history_store._encode_json_array.__code__.co_names
    assert "decode_json_array" in history_store._decode_json_array.__code__.co_names
    assert "encode_json_array" in history_route._history_results_json.__code__.co_names
