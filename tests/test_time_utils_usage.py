"""Contract tests for shared UTC helper usage at integration boundaries."""
from __future__ import annotations

from app.diagnostics import sources as diagnostic_sources
from app.enrichment import history_diagnostics
from app.routes import diagnostic_export
from app.routes import enrichment_diagnostics
from app.routes import diagnostics as diagnostics_route
from tests.test_dev_server import load_dev_server_module
from tests.test_optimization_audit import load_audit_module
from tests.test_runtime_state_repair import load_repair_module


def test_diagnostic_sources_use_shared_utc_iso_helper() -> None:
    assert "utcnow_iso" in diagnostic_sources._utcnow_iso.__code__.co_names


def test_route_helpers_use_shared_utc_iso_helper() -> None:
    assert "utcnow_iso" in history_diagnostics._utcnow_iso.__code__.co_names


def test_diagnostic_route_uses_shared_utc_helpers() -> None:
    assert not hasattr(diagnostics_route, "_utcnow")
    assert not hasattr(diagnostics_route, "_utc_iso")
    assert "utc_now" in diagnostic_export.diagnostic_export_route_response.__code__.co_names
    assert "utc_iso" in diagnostic_export.diagnostic_export_response.__code__.co_names


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
    assert (
        "stripped_bounded_non_whitespace"
        in history_diagnostics.coerce_history_save_diagnostics.__code__.co_names
    )
    assert (
        "stripped_bounded_non_whitespace"
        in enrichment_diagnostics._coerce_status_text_field.__code__.co_names
    )
    assert (
        "_coerce_status_text_field"
        in enrichment_diagnostics._coerce_orchestration_status_for_diagnostics.__code__.co_names
    )


def test_diagnostics_and_audit_use_shared_whitespace_collapse() -> None:
    from app.diagnostics import source_record_fields

    audit = load_audit_module()

    assert "collapse_whitespace" in source_record_fields._normalize_error_summary.__code__.co_names
    assert "collapse_whitespace" in audit.summarize_output.__code__.co_names


def test_byte_decoders_use_shared_utf8_replace_helper() -> None:
    from app.diagnostics import payload_encoding
    from app.enrichment.adapters import dns_txt
    from app.enrichment.adapters import asn_cymru, dns_lookup
    from app.ssh import line_streams

    assert "decode_utf8_replace" in payload_encoding.redact_and_encode_payload.__code__.co_names
    assert "_decode_txt_record" in dns_lookup._extract_txt_records.__code__.co_names
    assert "decode_txt_chunks" in dns_lookup._decode_txt_record.__code__.co_names
    assert "decode_txt_chunks" in asn_cymru._decode_txt_strings.__code__.co_names
    assert "decode_utf8_replace" in dns_txt.decode_txt_chunks.__code__.co_names
    assert "coerce_stream_line" in line_streams.iter_lines.__code__.co_names
    assert "decode_utf8_replace" in line_streams.coerce_stream_line.__code__.co_names


def test_diagnostic_assembler_uses_manifest_byte_serializer() -> None:
    from app.diagnostics import assembler

    assert "manifest_to_json_bytes" in assembler.assemble_diagnostic_bundle.__code__.co_names


def test_empty_json_literals_are_shared_across_runtime_modules() -> None:
    from app.routes import history_replay
    from app.json_utils import EMPTY_JSON_ARRAY, EMPTY_JSON_OBJECT

    assert EMPTY_JSON_OBJECT == "{}"
    assert EMPTY_JSON_ARRAY == "[]"
    assert history_replay.EMPTY_JSON_OBJECT is EMPTY_JSON_OBJECT


def test_empty_json_helpers_are_shared_across_runtime_modules() -> None:
    from app.cache import store as cache_store
    from app.enrichment import history_records
    from app.routes import history_replay

    assert "encode_json_object" in cache_store._encode_result_json.__code__.co_names
    assert "decode_json_object" in cache_store._decode_result_json.__code__.co_names
    assert "encode_json_array" in history_records._encode_json_array.__code__.co_names
    assert "decode_json_array" in history_records._decode_json_array.__code__.co_names
    assert "encode_json_array" in history_replay.history_results_json.__code__.co_names
