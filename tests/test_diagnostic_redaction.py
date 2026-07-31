"""Tests for diagnostic payload redaction primitives."""
from __future__ import annotations

import builtins
import inspect
import json
import re
from pathlib import Path

import app.diagnostics.redaction as redaction_module
import app.diagnostics.payload_redaction as payload_redaction
from app.diagnostics import text_rules
from app.diagnostics.payload_redaction import PAYLOAD_SEQUENCE_TYPES
from app.diagnostics.payload_rules import PAYLOAD_QUERY_NAMES, payload_key_redaction_label
from app.diagnostics.policy import DIAGNOSTIC_SANITIZATION_POLICY
from app.diagnostics.redaction import (
    RedactionMetadata,
    _RedactionAccumulator,
    append_ordered_redaction_label,
    _ordered_redaction_label_snapshot,
    redact_diagnostic_payload,
    redact_diagnostic_text,
)
from app.diagnostics.secret_inventory import (
    ConfiguredSecretInventory,
    _SecretCandidate,
    _SecretCollection,
    _append_configured_secret_candidate,
    append_provider_secret_candidate,
    append_longest_first_candidate,
    append_ordered_label,
    _candidate_label_tuple,
    _collect_configured_secret_candidates,
    collect_configured_secret_inventory,
    _normalize_label_part,
    _stable_keys,
    _stable_label_tuple,
    _trim_label_underscores,
    _stable_secret_candidates,
)
from app.diagnostics.text_rules import REDACTED_TEXT
from app.enrichment.config_store import ConfigStore


def _configured_store(tmp_path: Path) -> ConfigStore:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_vt_api_key("vt-live-secret-1234567890")
    store.set_provider_key("GreyNoise", "gn-live-secret-abcdef")
    store.set_provider_key("AbuseIPDB", "abuse-live-secret-xyz987")
    store.set_provider_key("EmailRep", "emailrep-live-secret-555")
    return store


def test_redaction_uses_shared_diagnostic_sanitization_policy_bounds() -> None:
    policy = DIAGNOSTIC_SANITIZATION_POLICY

    assert redaction_module.DEFAULT_MAX_REDACTION_DEPTH == policy.max_redaction_depth
    assert _normalize_label_part("X" * 200) == "x" * policy.max_redaction_label_chars


def test_label_part_normalization_uses_compiled_regex(monkeypatch) -> None:
    def fail_module_sub(*_args, **_kwargs):
        raise AssertionError("label normalization should use the compiled regex")

    monkeypatch.setattr("app.diagnostics.secret_inventory.re.sub", fail_module_sub)

    assert _normalize_label_part("Grey Noise!!") == "grey_noise"


def test_label_part_normalization_uses_index_trim_without_strip() -> None:
    class NoStripText(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("label normalization should avoid direct strip allocation")

    class NoStripLabel(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("label underscore trimming should scan directly")

    assert _normalize_label_part(NoStripText("  Grey Noise!!  ")) == "grey_noise"
    assert _trim_label_underscores(NoStripLabel("__grey_noise__")) == "grey_noise"
    assert "strip" not in _normalize_label_part.__code__.co_names
    assert "strip" not in _trim_label_underscores.__code__.co_names


def test_redaction_static_frozensets_avoid_temporary_set_literals() -> None:
    source = Path("app/diagnostics/redaction.py").read_text(encoding="utf-8")

    assert re.search(r"frozenset\s*\(\s*\{", source) is None


def test_redaction_records_use_slots_to_avoid_instance_dict() -> None:
    inventory = ConfiguredSecretInventory()
    metadata = RedactionMetadata(redaction_count=0, redaction_labels=())
    candidate = _SecretCandidate(label="configured_secret:test", value="secret-value")
    collection = _SecretCollection(candidates=(candidate,), inventory=inventory)
    accumulator = _RedactionAccumulator()

    assert not hasattr(inventory, "__dict__")
    assert not hasattr(metadata, "__dict__")
    assert not hasattr(candidate, "__dict__")
    assert not hasattr(collection, "__dict__")
    assert not hasattr(accumulator, "__dict__")


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


def test_payload_redaction_uses_direct_recursive_loops() -> None:
    import inspect

    class NoItemsDict(dict):
        def items(self):
            raise AssertionError("payload redaction should iterate dict keys directly")

    payload = NoItemsDict({"secret": "hidden-value", "items": ["Bearer token-value"]})
    acc = _RedactionAccumulator()

    redacted = payload_redaction.redact_payload_value(
        payload,
        (),
        acc,
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    )
    nested_code_names = {
        const.co_name
        for const in payload_redaction.redact_payload_mapping.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert redacted == {"secret": REDACTED_TEXT, "items": ["Bearer [REDACTED]"]}
    assert "redact_payload_mapping" in payload_redaction.redact_payload_value.__code__.co_names
    assert "for raw_key in value" not in inspect.getsource(payload_redaction.redact_payload_value)
    assert "for raw_key in value" in inspect.getsource(payload_redaction.redact_payload_mapping)
    assert "<listcomp>" not in nested_code_names


def test_payload_mapping_redaction_owns_key_policy_and_child_traversal() -> None:
    import inspect

    payload = {"api_key": "json-field-api-secret", "nested": {"token": "Bearer child-token"}}
    acc = _RedactionAccumulator()

    redacted = payload_redaction.redact_payload_mapping(
        payload,
        (),
        acc,
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    )
    mapping_source = inspect.getsource(payload_redaction.redact_payload_mapping)

    assert redacted == {
        "api_key": REDACTED_TEXT,
        "nested": {"token": REDACTED_TEXT},
    }
    assert "payload_key_redaction_label(" in mapping_source
    assert "redact_entire_scalar(" in mapping_source
    assert "redact_payload_value(" in mapping_source


def test_payload_sequence_types_share_recursive_helper(monkeypatch) -> None:
    calls: list[str] = []
    original = payload_redaction.redact_payload_sequence

    def redact_payload_sequence(
        value: list[object] | tuple[object, ...],
        candidates: tuple[object, ...],
        acc: _RedactionAccumulator,
        *,
        depth: int,
        seen: set[int],
        text_redactor,
        exact_secret_redactor,
    ) -> list[object]:
        calls.append(type(value).__name__)
        return original(
            value,
            candidates,
            acc,
            depth=depth,
            seen=seen,
            text_redactor=text_redactor,
            exact_secret_redactor=exact_secret_redactor,
        )

    monkeypatch.setattr(
        payload_redaction,
        "redact_payload_sequence",
        redact_payload_sequence,
    )

    redacted, metadata = redact_diagnostic_payload(
        {"tuple": ("Bearer tuple-token",), "list": ["Bearer list-token"]},
    )

    assert PAYLOAD_SEQUENCE_TYPES == (list, tuple)
    assert redacted == {
        "tuple": ["Bearer [REDACTED]"],
        "list": ["Bearer [REDACTED]"],
    }
    assert calls == ["tuple", "list"]
    assert metadata.redaction_count == 2


def test_payload_sequence_redaction_skips_iteration_for_empty_single_pair_three_or_four_sequence() -> None:
    class NoIterList(list):
        def __iter__(self):
            raise AssertionError("short payload sequences should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("payload sequence redaction should not slice")
            return super().__getitem__(index)

    acc = _RedactionAccumulator()

    assert payload_redaction.redact_payload_sequence(
        NoIterList([]),
        (),
        acc,
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    ) == []
    assert payload_redaction.redact_payload_sequence(
        NoIterList(["Bearer single-token"]),
        (),
        acc,
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    ) == ["Bearer [REDACTED]"]
    assert payload_redaction.redact_payload_sequence(
        NoIterList(["Bearer first-token", "Bearer second-token"]),
        (),
        acc,
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    ) == ["Bearer [REDACTED]", "Bearer [REDACTED]"]
    assert payload_redaction.redact_payload_sequence(
        NoIterList(["Bearer first-token", "Bearer second-token", "Bearer third-token"]),
        (),
        acc,
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    ) == ["Bearer [REDACTED]", "Bearer [REDACTED]", "Bearer [REDACTED]"]
    assert payload_redaction.redact_payload_sequence(
        NoIterList([
            "Bearer first-token",
            "Bearer second-token",
            "Bearer third-token",
            "Bearer fourth-token",
        ]),
        (),
        acc,
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    ) == [
        "Bearer [REDACTED]",
        "Bearer [REDACTED]",
        "Bearer [REDACTED]",
        "Bearer [REDACTED]",
    ]
    assert "len" in payload_redaction.redact_payload_sequence.__code__.co_names


def test_payload_sequence_redaction_uses_shared_child_boundary() -> None:
    import inspect

    source = inspect.getsource(payload_redaction.redact_payload_sequence)
    append_source = inspect.getsource(payload_redaction.append_redacted_payload_child)
    child_source = inspect.getsource(payload_redaction.redact_payload_child)

    redacted_items: list[object] = []
    payload_redaction.append_redacted_payload_child(
        redacted_items,
        "Bearer appended-token",
        (),
        _RedactionAccumulator(),
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    )

    assert redacted_items == ["Bearer [REDACTED]"]
    assert payload_redaction.redact_payload_child(
        "Bearer child-token",
        (),
        _RedactionAccumulator(),
        depth=5,
        seen=set(),
        text_redactor=text_rules.redact_text_with_candidates,
        exact_secret_redactor=text_rules.apply_exact_secret_redaction,
    ) == "Bearer [REDACTED]"
    assert "redact_payload_child(" in source
    assert "redact_payload_value(" not in source
    assert "append_redacted_payload_child(" in source
    assert "redacted_items.append(" not in source
    assert "redacted_items.append(" in append_source
    assert "redact_payload_child(" in append_source
    assert "redact_payload_value(" in child_source


def test_repeated_secret_occurrences_are_counted(tmp_path: Path) -> None:
    store = _configured_store(tmp_path)
    text = "vt-live-secret-1234567890 then vt-live-secret-1234567890"

    redacted, metadata = redact_diagnostic_text(text, config_store=store)

    assert "vt-live-secret-1234567890" not in redacted
    assert redacted.count(REDACTED_TEXT) == 2
    assert metadata.redaction_count == 2
    assert metadata.redaction_labels == ("configured_secret:virustotal",)


def test_exact_secret_redaction_reuses_preordered_candidates(monkeypatch) -> None:
    candidates = (
        _SecretCandidate(label="long", value="secret-value-long"),
        _SecretCandidate(label="short", value="secret-value"),
    )
    acc = _RedactionAccumulator()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("exact redaction should use preordered candidates")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    redacted = text_rules.apply_exact_secret_redaction(
        "token=secret-value-long",
        candidates,
        acc,
    )

    assert redacted == f"token={REDACTED_TEXT}"
    assert acc.count == 1
    assert acc.labels == {"long"}


def test_redaction_metadata_reuses_sorted_label_snapshot(monkeypatch) -> None:
    acc = _RedactionAccumulator()
    acc.add("pattern:field:secret")
    acc.note("configured_secret:virustotal")

    first = acc.metadata()

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("unchanged metadata labels should reuse the sorted snapshot")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    second = acc.metadata()
    acc.add("configured_secret:virustotal")
    third = acc.metadata()

    assert first.redaction_labels == (
        "configured_secret:virustotal",
        "pattern:field:secret",
    )
    assert second.redaction_labels == first.redaction_labels
    assert third.redaction_labels == first.redaction_labels


def test_redaction_accumulator_shares_label_dirty_tracking() -> None:
    source = Path("app/diagnostics/redaction.py").read_text(encoding="utf-8")

    assert "def _remember_label(self, label: str) -> None:" in source
    assert source.count("self._remember_label(label)") == 2
    assert source.count("self._labels_dirty = True") == 1


def test_redaction_metadata_uses_direct_ordered_label_insertion(monkeypatch) -> None:
    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("metadata should not sort label sets")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    empty = _RedactionAccumulator()
    single = _RedactionAccumulator()
    double = _RedactionAccumulator()
    triple = _RedactionAccumulator()
    quad = _RedactionAccumulator()
    single.add("configured_secret:virustotal")
    double.add("pattern:field:secret")
    double.note("configured_secret:virustotal")
    triple.add("pattern:field:secret")
    triple.note("configured_secret:virustotal")
    triple.note("pattern:authorization_bearer")
    quad.add("pattern:field:secret")
    quad.note("configured_secret:virustotal")
    quad.note("pattern:authorization_bearer")
    quad.note("pattern:query:api_key")

    assert empty.metadata().redaction_labels == ()
    assert single.metadata().redaction_labels == ("configured_secret:virustotal",)
    assert double.metadata().redaction_labels == (
        "configured_secret:virustotal",
        "pattern:field:secret",
    )
    assert triple.metadata().redaction_labels == (
        "configured_secret:virustotal",
        "pattern:authorization_bearer",
        "pattern:field:secret",
    )
    assert quad.metadata().redaction_labels == (
        "configured_secret:virustotal",
        "pattern:authorization_bearer",
        "pattern:field:secret",
        "pattern:query:api_key",
    )

    ordered_labels: list[str] = []
    append_ordered_redaction_label(ordered_labels, "pattern:field:secret")
    append_ordered_redaction_label(ordered_labels, "configured_secret:virustotal")
    append_ordered_redaction_label(ordered_labels, "pattern:query:api_key")
    append_ordered_redaction_label(ordered_labels, "pattern:authorization_bearer")
    assert ordered_labels == [
        "configured_secret:virustotal",
        "pattern:authorization_bearer",
        "pattern:field:secret",
        "pattern:query:api_key",
    ]


def test_redaction_metadata_uses_ordered_short_label_snapshot_helper() -> None:
    source = Path("app/diagnostics/redaction.py").read_text(encoding="utf-8")

    assert _ordered_redaction_label_snapshot({
        "pattern:field:secret",
        "configured_secret:virustotal",
        "pattern:authorization_bearer",
    }) == (
        "configured_secret:virustotal",
        "pattern:authorization_bearer",
        "pattern:field:secret",
    )
    assert _ordered_redaction_label_snapshot({
        "pattern:field:secret",
        "configured_secret:virustotal",
        "pattern:authorization_bearer",
        "pattern:query:api_key",
    }) == (
        "configured_secret:virustotal",
        "pattern:authorization_bearer",
        "pattern:field:secret",
        "pattern:query:api_key",
    )
    assert "_ordered_redaction_label_snapshot(self.labels)" in source
    assert "label_count == 4" in source
    assert "append_ordered_redaction_label" in _ordered_redaction_label_snapshot.__code__.co_names


def test_configured_secret_candidates_keep_longest_first_redaction(tmp_path: Path) -> None:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_vt_api_key("shared-secret-value-long")
    store.set_provider_key("Shorter", "shared-secret-value")

    redacted, metadata = redact_diagnostic_text(
        "overlap=shared-secret-value-long",
        config_store=store,
    )

    assert redacted == f"overlap={REDACTED_TEXT}"
    assert metadata.redaction_count == 1
    assert metadata.redaction_labels == ("configured_secret:virustotal",)


def test_configured_secret_candidate_order_uses_direct_longest_first_insertion() -> None:
    import inspect

    class SortFailingList(list):
        def sort(self, *_args, **_kwargs):
            raise AssertionError("configured secret candidates should not sort")

    candidate = _SecretCandidate(
        label="configured_secret:provider:greynoise",
        value="grey-secret-value-123456",
    )
    shorter_candidate = _SecretCandidate(
        label="configured_secret:provider:abuseipdb",
        value="abuse-secret-value",
    )
    middle_candidate = _SecretCandidate(
        label="configured_secret:provider:emailrep",
        value="emailrep-secret-value",
    )
    longest_candidate = _SecretCandidate(
        label="configured_secret:provider:virustotal",
        value="virustotal-secret-value-1234567890",
    )

    assert _stable_secret_candidates(SortFailingList()) == ()
    assert _stable_secret_candidates(SortFailingList([candidate])) == (candidate,)
    assert _stable_secret_candidates(SortFailingList([shorter_candidate, candidate])) == (
        candidate,
        shorter_candidate,
    )
    assert _stable_secret_candidates(SortFailingList([candidate, shorter_candidate])) == (
        candidate,
        shorter_candidate,
    )
    assert _stable_secret_candidates(SortFailingList([candidate, shorter_candidate, longest_candidate])) == (
        longest_candidate,
        candidate,
        shorter_candidate,
    )
    assert _stable_secret_candidates(
        SortFailingList([candidate, shorter_candidate, middle_candidate, longest_candidate])
    ) == (
        longest_candidate,
        candidate,
        middle_candidate,
        shorter_candidate,
    )
    assert "candidate_count == 4" in inspect.getsource(_stable_secret_candidates)

    ordered: list[_SecretCandidate] = []
    append_longest_first_candidate(ordered, shorter_candidate)
    append_longest_first_candidate(ordered, candidate)
    append_longest_first_candidate(ordered, middle_candidate)
    append_longest_first_candidate(ordered, longest_candidate)
    assert ordered == [longest_candidate, candidate, middle_candidate, shorter_candidate]


def test_configured_secret_candidate_append_owns_validation_and_construction() -> None:
    candidates: list[_SecretCandidate] = []

    assert _append_configured_secret_candidate(
        candidates,
        label="configured_secret:provider:alpha",
        raw_secret="  secret-value-alpha  ",
    ) is True
    assert _append_configured_secret_candidate(
        candidates,
        label="configured_secret:provider:short",
        raw_secret="short",
    ) is False
    assert _append_configured_secret_candidate(
        candidates,
        label="configured_secret:provider:none",
        raw_secret=None,
    ) is False

    assert candidates == [
        _SecretCandidate(label="configured_secret:provider:alpha", value="secret-value-alpha")
    ]


def test_candidate_label_tuple_owns_secret_label_projection(monkeypatch) -> None:
    import inspect

    candidate = _SecretCandidate(
        label="configured_secret:provider:greynoise",
        value="grey-secret-value-123456",
    )
    shorter_candidate = _SecretCandidate(
        label="configured_secret:provider:abuseipdb",
        value="abuse-secret-value",
    )
    middle_candidate = _SecretCandidate(
        label="configured_secret:provider:emailrep",
        value="emailrep-secret-value",
    )
    fourth_candidate = _SecretCandidate(
        label="configured_secret:provider:virustotal",
        value="virustotal-secret-value",
    )

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("zero or single candidate label projection should not sort")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    assert _candidate_label_tuple(()) == ()
    assert _candidate_label_tuple((candidate,)) == ("configured_secret:provider:greynoise",)
    monkeypatch.undo()
    assert _candidate_label_tuple((candidate, shorter_candidate)) == (
        "configured_secret:provider:abuseipdb",
        "configured_secret:provider:greynoise",
    )
    assert _candidate_label_tuple((candidate, shorter_candidate, middle_candidate)) == (
        "configured_secret:provider:abuseipdb",
        "configured_secret:provider:emailrep",
        "configured_secret:provider:greynoise",
    )
    assert _candidate_label_tuple((candidate, shorter_candidate, middle_candidate, fourth_candidate)) == (
        "configured_secret:provider:abuseipdb",
        "configured_secret:provider:emailrep",
        "configured_secret:provider:greynoise",
        "configured_secret:provider:virustotal",
    )
    assert "append_candidate_label" in _candidate_label_tuple.__code__.co_names
    assert "labels.append(candidate.label)" not in inspect.getsource(_candidate_label_tuple)
    assert "candidate_count == 4" in inspect.getsource(_candidate_label_tuple)


def test_configured_secret_inventory_deduplicates_provider_labels_directly(monkeypatch) -> None:
    class FakeConfigStore:
        def get_vt_api_key(self) -> str:
            return ""

        def all_provider_keys(self) -> dict[str, str]:
            return {
                "Grey Noise": "grey-secret-value-123456",
                "grey_noise": "other-grey-secret-value-123456",
            }

    def fail_set(*_args, **_kwargs):
        raise AssertionError("provider label inventory should deduplicate during collection")

    monkeypatch.setattr(builtins, "set", fail_set)

    inventory = collect_configured_secret_inventory(FakeConfigStore())

    assert inventory.provider_labels == ("grey_noise",)
    assert inventory.secret_labels == (
        "configured_secret:provider:grey_noise",
        "configured_secret:provider:grey_noise",
    )


def test_configured_secret_collection_skips_sort_for_single_provider(monkeypatch) -> None:
    class FakeConfigStore:
        def get_vt_api_key(self) -> str:
            return ""

        def all_provider_keys(self) -> dict[str, str]:
            return {"Grey Noise": "grey-secret-value-123456"}

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("single-provider inventory should not call sorted()")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    collection = _collect_configured_secret_candidates(FakeConfigStore())

    assert collection.inventory.provider_labels == ("grey_noise",)
    assert collection.inventory.secret_labels == (
        "configured_secret:provider:grey_noise",
    )
    assert [candidate.label for candidate in collection.candidates] == [
        "configured_secret:provider:grey_noise",
    ]


def test_configured_secret_collection_accepts_explicit_store_factory() -> None:
    import inspect

    class FakeConfigStore:
        def get_vt_api_key(self) -> str:
            return "vt-secret-value-123456"

        def all_provider_keys(self) -> dict[str, str]:
            return {"Alpha": "alpha-secret-value-123456"}

    created: list[str] = []

    def make_store() -> FakeConfigStore:
        created.append("store")
        return FakeConfigStore()

    collection = _collect_configured_secret_candidates(
        config_store_factory=make_store,
    )
    inventory = collect_configured_secret_inventory(
        config_store_factory=make_store,
    )
    collector_source = inspect.getsource(_collect_configured_secret_candidates)
    public_source = inspect.getsource(collect_configured_secret_inventory)

    assert created == ["store", "store"]
    assert collection.inventory.provider_labels == ("alpha",)
    assert collection.inventory.secret_labels == (
        "configured_secret:provider:alpha",
        "configured_secret:virustotal",
    )
    assert inventory.provider_labels == ("alpha",)
    assert inventory.secret_labels == collection.inventory.secret_labels
    assert "config_store_factory()" in collector_source
    assert "ConfigStore()" not in collector_source
    assert "config_store_factory=config_store_factory" in public_source


def test_stable_key_and_label_helpers_use_direct_ordered_insertion(monkeypatch) -> None:
    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("stable helpers should not call sorted()")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    assert _stable_keys({"zeta": "1", "alpha": "2"}) == ("alpha", "zeta")
    assert _stable_label_tuple(["zeta", "alpha"]) == ("alpha", "zeta")
    assert _stable_label_tuple({"zeta": None, "alpha": None}) == ("alpha", "zeta")
    assert _stable_keys({"zeta": "1", "alpha": "2", "middle": "3"}) == (
        "alpha",
        "middle",
        "zeta",
    )
    assert _stable_label_tuple(["zeta", "alpha", "middle"]) == (
        "alpha",
        "middle",
        "zeta",
    )
    assert _stable_label_tuple({"zeta": None, "alpha": None, "middle": None}) == (
        "alpha",
        "middle",
        "zeta",
    )
    assert _stable_keys({"zeta": "1", "alpha": "2", "middle": "3", "beta": "4"}) == (
        "alpha",
        "beta",
        "middle",
        "zeta",
    )
    assert _stable_label_tuple(["zeta", "alpha", "middle", "alpha"]) == (
        "alpha",
        "alpha",
        "middle",
        "zeta",
    )
    assert "key_count == 4" in inspect.getsource(_stable_keys)
    assert "label_count == 4" in inspect.getsource(_stable_label_tuple)

    ordered_labels: list[str] = []
    append_ordered_label(ordered_labels, "zeta")
    append_ordered_label(ordered_labels, "alpha")
    append_ordered_label(ordered_labels, "middle")
    append_ordered_label(ordered_labels, "alpha")
    assert ordered_labels == ["alpha", "alpha", "middle", "zeta"]


def test_configured_secret_collection_avoids_item_pairs_and_generator_frames() -> None:
    class NoItemsDict(dict):
        def items(self):
            raise AssertionError("configured secret collection should sort provider keys directly")

    class FakeConfigStore:
        def get_vt_api_key(self) -> str:
            return "vt-secret-value-123456"

        def all_provider_keys(self) -> dict[str, str]:
            return NoItemsDict(
                {
                    "Zed": "zed-secret-value-123456",
                    "Alpha": "alpha-secret-value-123456",
                }
            )

    collection = _collect_configured_secret_candidates(FakeConfigStore())
    nested_code_names = {
        const.co_name
        for const in _collect_configured_secret_candidates.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert collection.inventory.provider_labels == ("alpha", "zed")
    assert collection.inventory.secret_labels == (
        "configured_secret:provider:alpha",
        "configured_secret:provider:zed",
        "configured_secret:virustotal",
    )
    assert "<genexpr>" not in nested_code_names
    assert "_append_configured_secret_candidate" in _collect_configured_secret_candidates.__code__.co_names
    assert "append_provider_secret_candidate" in _collect_configured_secret_candidates.__code__.co_names
    assert "_candidate_label_tuple" in _collect_configured_secret_candidates.__code__.co_names
    assert "_SecretCandidate" not in _collect_configured_secret_candidates.__code__.co_names
    collector_source = inspect.getsource(_collect_configured_secret_candidates)
    helper_source = inspect.getsource(append_provider_secret_candidate)
    assert "_normalize_label_part(raw_provider_name)" not in collector_source
    assert "provider_labels[provider_label] = None" not in collector_source
    assert "_normalize_label_part(raw_provider_name)" in helper_source
    assert "provider_labels[provider_label] = None" in helper_source


def test_provider_secret_candidate_helper_owns_provider_label_state() -> None:
    candidates: list[_SecretCandidate] = []
    provider_labels: dict[str, None] = {}

    append_provider_secret_candidate(
        candidates,
        provider_labels,
        "Grey Noise",
        "greynoise-secret-value-123456",
    )
    append_provider_secret_candidate(candidates, provider_labels, "Too Short", "tiny")

    assert candidates == [
        _SecretCandidate(
            label="configured_secret:provider:grey_noise",
            value="greynoise-secret-value-123456",
        )
    ]
    assert provider_labels == {"grey_noise": None}


def test_configured_secret_collection_trims_secrets_without_strip() -> None:
    class NoStripSecret(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("configured secret collection should avoid direct strip allocation")

    class FakeConfigStore:
        def get_vt_api_key(self) -> str:
            return NoStripSecret("  vt-secret-value-123456  ")

        def all_provider_keys(self) -> dict[str, str]:
            return {
                "Alpha": NoStripSecret("  alpha-secret-value-123456  "),
                "Short": NoStripSecret("  tiny  "),
            }

    collection = _collect_configured_secret_candidates(FakeConfigStore())

    assert sorted(candidate.value for candidate in collection.candidates) == [
        "alpha-secret-value-123456",
        "vt-secret-value-123456",
    ]


def test_payload_field_redaction_trims_keys_and_scalars_without_strip() -> None:
    class NoStripText(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("payload redaction should avoid direct strip allocation")

    payload = {
        NoStripText(" api_key "): NoStripText("  json-field-api-secret  "),
        NoStripText(" authorization "): NoStripText("  Bearer runtime-token-value  "),
    }

    redacted, metadata = redact_diagnostic_payload(payload, config_store=None)

    assert redacted == {
        " api_key ": REDACTED_TEXT,
        " authorization ": f"Bearer {REDACTED_TEXT}",
    }
    assert "pattern:field:api_key" in metadata.redaction_labels
    assert "pattern:authorization_bearer" in metadata.redaction_labels


def test_payload_key_redaction_rules_live_outside_recursive_traversal() -> None:
    import inspect

    rule_source = inspect.getsource(payload_key_redaction_label)
    facade_source = inspect.getsource(redaction_module.redact_diagnostic_payload)
    traversal_source = inspect.getsource(payload_redaction.redact_payload_value)
    mapping_source = inspect.getsource(payload_redaction.redact_payload_mapping)

    assert payload_key_redaction_label(" api_key ") == "pattern:field:api_key"
    assert payload_key_redaction_label(" authorization ") == "pattern:authorization_bearer"
    assert payload_key_redaction_label(" X-Api-Key ") == "pattern:header:x-api-key"
    assert payload_key_redaction_label("provider") is None
    assert "redact_payload_value(" in facade_source
    assert "redact_payload_mapping(" in traversal_source
    assert "payload_key_redaction_label(" in mapping_source
    assert "stripped_text_or_none(" in rule_source


def test_redaction_delegates_payload_traversal_engine() -> None:
    import inspect

    module_source = inspect.getsource(redaction_module)
    facade_source = inspect.getsource(redaction_module.redact_diagnostic_payload)
    traversal_source = inspect.getsource(payload_redaction.redact_payload_value)

    assert "redact_payload_value(" in facade_source
    assert "def _redact_payload_value" not in module_source
    assert "def _redact_payload_sequence" not in module_source
    assert "_PAYLOAD_SEQUENCE_TYPES" not in module_source
    assert "_PAYLOAD_CONTAINER_TYPES" not in module_source
    assert "for raw_key in value" not in facade_source
    assert "seen.add(value_id)" not in facade_source
    assert "redact_payload_mapping(" in traversal_source
    assert "seen.add(value_id)" in traversal_source


def test_redaction_facade_does_not_reexport_owner_module_internals() -> None:
    assert not hasattr(redaction_module, "_SecretCandidate")
    assert not hasattr(redaction_module, "_normalize_label_part")
    assert not hasattr(redaction_module, "_stable_secret_candidates")
    assert not hasattr(redaction_module, "_PAYLOAD_SEQUENCE_TYPES")
    assert not hasattr(redaction_module, "PAYLOAD_SEQUENCE_TYPES")
    assert not hasattr(redaction_module, "REDACTED_TEXT")
    assert not hasattr(redaction_module, "ConfiguredSecretInventory")
    assert not hasattr(redaction_module, "collect_configured_secret_inventory")
    assert not hasattr(redaction_module, "ConfigSecretStore")
    assert "MIN_CONFIGURED_SECRET_CHARS" not in redaction_module.__all__
    assert "_RedactionAccumulator" not in redaction_module.__all__
    assert "ConfiguredSecretInventory" not in redaction_module.__all__
    assert "collect_configured_secret_inventory" not in redaction_module.__all__
    assert "ConfigSecretStore" not in redaction_module.__all__


def test_exact_secret_redaction_delegates_text_rule_helper() -> None:
    import inspect

    facade_source = inspect.getsource(text_rules.redact_text_with_candidates)
    module_source = inspect.getsource(redaction_module)
    helper_source = inspect.getsource(text_rules.apply_exact_secret_redaction)
    candidates = (
        _SecretCandidate(label="configured_secret:provider", value="secret-value-long"),
    )
    acc = _RedactionAccumulator()

    redacted = text_rules.apply_exact_secret_redaction(
        "token=secret-value-long",
        candidates,
        acc,
    )

    assert redacted == f"token={REDACTED_TEXT}"
    assert acc.count == 1
    assert "apply_exact_secret_redaction(" in facade_source
    assert not hasattr(redaction_module, "_redact_text_with_candidates")
    assert "def _apply_exact_secret_redaction" not in module_source
    assert "for secret in candidates" not in facade_source
    assert ".replace(" not in facade_source
    assert "for secret in candidates" in helper_source
    assert ".replace(" in helper_source


def test_text_pattern_redaction_delegates_rule_engine() -> None:
    import inspect

    facade_source = inspect.getsource(text_rules.redact_text_with_candidates)
    module_source = inspect.getsource(redaction_module)
    rule_source = inspect.getsource(text_rules.apply_text_pattern_redaction)
    helper_source = inspect.getsource(text_rules._apply_text_rule)

    acc = _RedactionAccumulator()
    redacted = text_rules.apply_text_pattern_redaction(
        "authorization: Bearer runtime-token-value",
        acc,
    )

    assert redacted == f"authorization: Bearer {REDACTED_TEXT}"
    assert acc.count == 1
    assert "apply_text_pattern_redaction(" in facade_source
    assert not hasattr(redaction_module, "_redact_text_with_candidates")
    assert "def _apply_pattern_redaction" not in module_source
    assert ".regex.sub(" not in facade_source
    assert "for rule in _TEXT_RULES" in rule_source
    assert "_apply_text_rule(" in rule_source
    assert ".regex.sub(" not in rule_source
    assert ".regex.sub(" in helper_source


def test_text_pattern_rules_use_direct_fixed_query_and_field_rules() -> None:
    import inspect

    labels = tuple(rule.label for rule in text_rules._TEXT_RULES)
    module_source = Path("app/diagnostics/text_rules.py").read_text(encoding="utf-8")
    rules_source = module_source.split("_TEXT_RULES = (", 1)[1].split(")\n\n\ndef apply_exact_secret_redaction", 1)[0]

    assert tuple(f"pattern:query:{name}" for name in PAYLOAD_QUERY_NAMES) == labels[5:9]
    assert tuple(f"pattern:field:{name}" for name in PAYLOAD_QUERY_NAMES) == labels[9:13]
    assert "_query_secret_rule(\"api_key\")" in rules_source
    assert "_query_secret_rule(\"secret\")" in rules_source
    assert "_jsonish_field_rule(\"api_key\")" in rules_source
    assert "_jsonish_field_rule(\"secret\")" in rules_source
    assert "for name in PAYLOAD_QUERY_NAMES" not in rules_source
    assert "*(" not in rules_source
    assert "PAYLOAD_QUERY_NAMES" not in inspect.getsource(text_rules)


def test_apply_text_rule_owns_callback_replacement_counting() -> None:
    import inspect

    rule = next(
        rule
        for rule in text_rules._TEXT_RULES
        if rule.label == "pattern:header:x-api-key"
    )
    acc = _RedactionAccumulator()

    redacted = text_rules._apply_text_rule(
        "x-api-key: first x-api-key: [REDACTED]",
        rule,
        acc,
    )

    assert redacted == f"x-api-key: {REDACTED_TEXT} x-api-key: [REDACTED]"
    assert acc.count == 1
    assert "_callback" in inspect.getsource(text_rules._apply_text_rule)


def test_config_read_error_metadata_is_secret_free_and_label_bounded() -> None:
    class FailingStore:
        def get_vt_api_key(self) -> str | None:
            raise RuntimeError("failed reading vt-secret-value-should-not-leak")

        def all_provider_keys(self) -> dict[str, str]:
            raise AssertionError("should not read provider keys after VT failure")

    redacted, metadata = redact_diagnostic_text(
        "authorization: Bearer runtime-token-value",
        config_store=FailingStore(),
    )

    assert "runtime-token-value" not in redacted
    assert "vt-secret-value-should-not-leak" not in json.dumps(metadata.__dict__ if hasattr(metadata, "__dict__") else repr(metadata))
    assert metadata.config_error == "config_read_failed"
    assert "config:read_failed" in metadata.redaction_labels
    assert all(
        len(label) <= DIAGNOSTIC_SANITIZATION_POLICY.max_redaction_label_chars
        for label in metadata.redaction_labels
    )
