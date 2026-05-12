"""Tests for diagnostic payload redaction primitives."""
from __future__ import annotations

import json
from pathlib import Path

from app.diagnostics.redaction import (
    REDACTED_TEXT,
    collect_configured_secret_inventory,
    redact_diagnostic_payload,
    redact_diagnostic_text,
)
from app.enrichment.config_store import ConfigStore


def _configured_store(tmp_path: Path) -> ConfigStore:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_vt_api_key("vt-live-secret-1234567890")
    store.set_provider_key("GreyNoise", "gn-live-secret-abcdef")
    store.set_provider_key("AbuseIPDB", "abuse-live-secret-xyz987")
    store.set_provider_key("EmailRep", "emailrep-live-secret-555")
    return store


def _dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def test_collect_configured_secret_inventory_labels_without_values(tmp_path: Path) -> None:
    store = _configured_store(tmp_path)

    inventory = collect_configured_secret_inventory(store)
    dumped = _dump(inventory)

    assert set(inventory.secret_labels) == {
        "configured_secret:virustotal",
        "configured_secret:provider:abuseipdb",
        "configured_secret:provider:emailrep",
        "configured_secret:provider:greynoise",
    }
    assert inventory.config_error is None
    assert inventory.provider_labels == ("abuseipdb", "emailrep", "greynoise")
    assert "vt-live-secret-1234567890" not in dumped
    assert "gn-live-secret-abcdef" not in dumped
    assert "abuse-live-secret-xyz987" not in dumped
    assert "emailrep-live-secret-555" not in dumped


def test_redacts_configured_secrets_and_common_patterns_in_nested_payload(
    tmp_path: Path,
) -> None:
    store = _configured_store(tmp_path)
    original = {
        "provider": "EmailRep",
        "ioc": "198.51.100.42",
        "verdict": "suspicious",
        "count": 3,
        "headers": {
            "Authorization": "Bearer runtime-bearer-token-123",
            "X-Api-Key": "x-api-runtime-secret",
            "Auth-Key": "auth-runtime-secret",
            "Key": "emailrep-runtime-secret",
            "Content-Type": "application/json",
        },
        "url": (
            "https://api.example.test/lookup?ioc=198.51.100.42"
            "&api_key=query-api-secret&token=query-token-secret&secret=query-secret-value"
        ),
        "error": (
            "VT failed with vt-live-secret-1234567890; "
            "GreyNoise key=gn-live-secret-abcdef; apikey=inline-api-secret"
        ),
        "nested": [
            {"api_key": "json-field-api-secret", "timestamp": "2026-01-02T03:04:05Z"},
            ["abuse-live-secret-xyz987", "emailrep-live-secret-555"],
        ],
    }

    redacted, metadata = redact_diagnostic_payload(original, config_store=store)
    dumped = _dump(redacted)
    original_dump = _dump(original)

    for forbidden in [
        "vt-live-secret-1234567890",
        "gn-live-secret-abcdef",
        "abuse-live-secret-xyz987",
        "emailrep-live-secret-555",
        "runtime-bearer-token-123",
        "x-api-runtime-secret",
        "auth-runtime-secret",
        "emailrep-runtime-secret",
        "query-api-secret",
        "query-token-secret",
        "query-secret-value",
        "inline-api-secret",
        "json-field-api-secret",
    ]:
        assert forbidden not in dumped

    assert "EmailRep" in dumped
    assert "198.51.100.42" in dumped
    assert "suspicious" in dumped
    assert "2026-01-02T03:04:05Z" in dumped
    assert original_dump != dumped
    assert "vt-live-secret-1234567890" in original_dump
    assert metadata.redaction_count >= 12
    assert metadata.redaction_labels == tuple(sorted(metadata.redaction_labels))
    assert "configured_secret:virustotal" in metadata.redaction_labels
    assert "configured_secret:provider:greynoise" in metadata.redaction_labels
    assert "pattern:authorization_bearer" in metadata.redaction_labels
    assert "pattern:header:x-api-key" in metadata.redaction_labels
    assert "pattern:query:api_key" in metadata.redaction_labels
    assert "pattern:field:api_key" in metadata.redaction_labels
    assert "pattern:header:key" in metadata.redaction_labels
    assert not any("secret-" in label or "token-" in label for label in metadata.redaction_labels)


def test_redact_diagnostic_text_is_case_insensitive_for_auth_names(tmp_path: Path) -> None:
    store = _configured_store(tmp_path)
    text = (
        "authorization: bearer MIXED-BEARER-VALUE\n"
        "x-api-key: MIXED-X-API-KEY\n"
        "AUTH-KEY: MIXED-AUTH-KEY\n"
        "key: MIXED-EMAILREP-KEY\n"
        "url=https://example.test/path?Api_Key=MIXED-QUERY-KEY&ToKeN=MIXED-TOKEN"
    )

    redacted, metadata = redact_diagnostic_text(text, config_store=store)

    assert "MIXED-BEARER-VALUE" not in redacted
    assert "MIXED-X-API-KEY" not in redacted
    assert "MIXED-AUTH-KEY" not in redacted
    assert "MIXED-EMAILREP-KEY" not in redacted
    assert "MIXED-QUERY-KEY" not in redacted
    assert "MIXED-TOKEN" not in redacted
    assert "authorization: Bearer" in redacted
    assert metadata.redaction_count == 6
    assert "pattern:authorization_bearer" in metadata.redaction_labels


def test_short_configured_values_are_not_globally_redacted_but_patterns_are(tmp_path: Path) -> None:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_vt_api_key("ioc")
    store.set_provider_key("greynoise", "key")
    payload = {
        "ioc": "ioc",
        "provider": "GreyNoise",
        "sentence": "short key and ioc words should remain",
        "headers": {"X-Api-Key": "short-pattern-secret"},
    }

    redacted, metadata = redact_diagnostic_payload(payload, config_store=store)
    dumped = _dump(redacted)

    assert '"ioc": "ioc"' in dumped
    assert "short key and ioc words should remain" in dumped
    assert "short-pattern-secret" not in dumped
    assert "pattern:header:x-api-key" in metadata.redaction_labels
    assert "configured_secret:virustotal" not in metadata.redaction_labels
    assert "configured_secret:provider:greynoise" not in metadata.redaction_labels


def test_missing_or_failing_config_degrades_to_pattern_only(tmp_path: Path) -> None:
    missing_store = ConfigStore(config_path=tmp_path / "missing" / "config.ini")
    payload = {
        "ioc": "evil.example",
        "url": "https://api.example.test/?secret=query-secret",
        "error": "Authorization: Bearer fallback-token",
    }

    redacted, metadata = redact_diagnostic_payload(payload, config_store=missing_store)
    dumped = _dump(redacted)

    assert "evil.example" in dumped
    assert "query-secret" not in dumped
    assert "fallback-token" not in dumped
    assert metadata.config_error is None
    assert "pattern:query:secret" in metadata.redaction_labels

    class FailingStore:
        def get_vt_api_key(self) -> str | None:
            raise OSError("permission denied while reading config")

        def all_provider_keys(self) -> dict[str, str]:
            raise OSError("permission denied while reading providers")

    redacted_again, metadata_again = redact_diagnostic_payload(payload, config_store=FailingStore())
    dumped_again = _dump(redacted_again)

    assert "query-secret" not in dumped_again
    assert "fallback-token" not in dumped_again
    assert metadata_again.config_error == "config_read_failed"
    assert "config:read_failed" in metadata_again.redaction_labels


def test_payload_redaction_is_deterministic_and_does_not_mutate_input(tmp_path: Path) -> None:
    store = _configured_store(tmp_path)
    payload = {
        "authorization": "Bearer deterministic-token",
        "nested": [{"token": "json-token-secret"}],
        "provider": "VirusTotal",
    }
    before = _dump(payload)

    first, first_metadata = redact_diagnostic_payload(payload, config_store=store)
    second, second_metadata = redact_diagnostic_payload(payload, config_store=store)

    assert _dump(payload) == before
    assert _dump(first) == _dump(second)
    assert first_metadata == second_metadata
    assert "deterministic-token" not in _dump(first)
    assert "json-token-secret" not in _dump(first)


def test_malformed_scalars_and_cycles_are_handled_safely(tmp_path: Path) -> None:
    store = _configured_store(tmp_path)
    cyclic: dict[str, object] = {"ioc": "203.0.113.9"}
    cyclic["self"] = cyclic
    cyclic["bad"] = object()
    cyclic["secret"] = "cycle-secret-value"

    redacted, metadata = redact_diagnostic_payload(cyclic, config_store=store)
    dumped = _dump(redacted)

    assert "203.0.113.9" in dumped
    assert "cycle-secret-value" not in dumped
    assert REDACTED_TEXT in dumped
    assert "[Circular]" in dumped
    assert "[Unserializable:object]" in dumped
    assert "pattern:field:secret" in metadata.redaction_labels


def test_repeated_secret_occurrences_are_counted(tmp_path: Path) -> None:
    store = _configured_store(tmp_path)
    text = "vt-live-secret-1234567890 then vt-live-secret-1234567890"

    redacted, metadata = redact_diagnostic_text(text, config_store=store)

    assert "vt-live-secret-1234567890" not in redacted
    assert redacted.count(REDACTED_TEXT) == 2
    assert metadata.redaction_count == 2
    assert metadata.redaction_labels == ("configured_secret:virustotal",)
