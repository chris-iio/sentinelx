"""Tests for diagnostic payload redaction primitives."""
from __future__ import annotations

import builtins
import json
import re
from pathlib import Path

import app.diagnostics.redaction as redaction_module
from app.diagnostics.policy import DIAGNOSTIC_SANITIZATION_POLICY
from app.diagnostics.redaction import (
    ConfiguredSecretInventory,
    REDACTED_TEXT,
    RedactionMetadata,
    _RedactionAccumulator,
    _SecretCandidate,
    _SecretCollection,
    _apply_exact_secret_redaction,
    _collect_configured_secret_candidates,
    _normalize_label_part,
    _PAYLOAD_SEQUENCE_TYPES,
    _redact_payload_sequence,
    _stable_keys,
    _stable_label_tuple,
    _trim_label_underscores,
    _stable_secret_candidates,
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


def test_redaction_uses_shared_diagnostic_sanitization_policy_bounds() -> None:
    policy = DIAGNOSTIC_SANITIZATION_POLICY

    assert redaction_module.DEFAULT_MAX_REDACTION_DEPTH == policy.max_redaction_depth
    assert _normalize_label_part("X" * 200) == "x" * policy.max_redaction_label_chars


def test_label_part_normalization_uses_compiled_regex(monkeypatch) -> None:
    def fail_module_sub(*_args, **_kwargs):
        raise AssertionError("label normalization should use the compiled regex")

    monkeypatch.setattr("app.diagnostics.redaction.re.sub", fail_module_sub)

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
    from app.diagnostics.redaction import _redact_payload_value

    class NoItemsDict(dict):
        def items(self):
            raise AssertionError("payload redaction should iterate dict keys directly")

    payload = NoItemsDict({"secret": "hidden-value", "items": ["Bearer token-value"]})
    acc = _RedactionAccumulator()

    redacted = _redact_payload_value(payload, (), acc, depth=5, seen=set())
    nested_code_names = {
        const.co_name
        for const in _redact_payload_value.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert redacted == {"secret": REDACTED_TEXT, "items": ["Bearer [REDACTED]"]}
    assert "<listcomp>" not in nested_code_names


def test_payload_sequence_types_share_recursive_helper(monkeypatch) -> None:
    import app.diagnostics.redaction as redaction

    calls: list[str] = []
    original = redaction._redact_payload_sequence

    def redact_payload_sequence(
        value: list[object] | tuple[object, ...],
        candidates: tuple[_SecretCandidate, ...],
        acc: _RedactionAccumulator,
        *,
        depth: int,
        seen: set[int],
    ) -> list[object]:
        calls.append(type(value).__name__)
        return original(value, candidates, acc, depth=depth, seen=seen)

    monkeypatch.setattr(redaction, "_redact_payload_sequence", redact_payload_sequence)

    redacted, metadata = redaction.redact_diagnostic_payload(
        {"tuple": ("Bearer tuple-token",), "list": ["Bearer list-token"]},
    )

    assert _PAYLOAD_SEQUENCE_TYPES == (list, tuple)
    assert redacted == {
        "tuple": ["Bearer [REDACTED]"],
        "list": ["Bearer [REDACTED]"],
    }
    assert calls == ["tuple", "list"]
    assert metadata.redaction_count == 2


def test_payload_sequence_redaction_skips_iteration_for_empty_single_or_pair_sequence() -> None:
    class NoIterList(list):
        def __iter__(self):
            raise AssertionError("short payload sequences should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("payload sequence redaction should not slice")
            return super().__getitem__(index)

    acc = _RedactionAccumulator()

    assert _redact_payload_sequence(NoIterList([]), (), acc, depth=5, seen=set()) == []
    assert _redact_payload_sequence(
        NoIterList(["Bearer single-token"]),
        (),
        acc,
        depth=5,
        seen=set(),
    ) == ["Bearer [REDACTED]"]
    assert _redact_payload_sequence(
        NoIterList(["Bearer first-token", "Bearer second-token"]),
        (),
        acc,
        depth=5,
        seen=set(),
    ) == ["Bearer [REDACTED]", "Bearer [REDACTED]"]
    assert "len" in _redact_payload_sequence.__code__.co_names


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

    redacted = _apply_exact_secret_redaction("token=secret-value-long", candidates, acc)

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


def test_redaction_metadata_skips_sort_for_zero_or_one_label(monkeypatch) -> None:
    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("metadata should not sort empty or single-label sets")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    empty = _RedactionAccumulator()
    single = _RedactionAccumulator()
    single.add("configured_secret:virustotal")

    assert empty.metadata().redaction_labels == ()
    assert single.metadata().redaction_labels == ("configured_secret:virustotal",)


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


def test_configured_secret_candidate_order_skips_sort_for_zero_one_two_or_three_candidates() -> None:
    class SortFailingList(list):
        def sort(self, *_args, **_kwargs):
            raise AssertionError("zero, one, two, or three configured secret candidates should not sort")

    candidate = _SecretCandidate(
        label="configured_secret:provider:greynoise",
        value="grey-secret-value-123456",
    )
    shorter_candidate = _SecretCandidate(
        label="configured_secret:provider:abuseipdb",
        value="abuse-secret-value",
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


def test_stable_key_and_label_helpers_skip_sort_for_two_or_three_values(monkeypatch) -> None:
    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("short stable helpers should not call sorted()")

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
