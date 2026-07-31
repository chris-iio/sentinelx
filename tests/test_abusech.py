"""Tests for shared abuse.ch adapter response helpers."""
from __future__ import annotations

import inspect

from app.enrichment.adapters.abusech import abusech_data_records, abusech_query_status


class NoDefaultBody(dict):
    def get(self, key, default=None):
        if key == "query_status" and default != "":
            raise AssertionError("abuse.ch query_status fallback should be the provider empty string")
        if key == "data" and default is not None:
            raise AssertionError("abuse.ch data parsing should avoid eager defaults")
        return super().get(key, default)


def test_query_status_helper_preserves_provider_fallback() -> None:
    """abuse.ch query-status extraction should preserve the empty-string fallback."""
    assert abusech_query_status({"query_status": "is_listed"}) == "is_listed"
    assert abusech_query_status(NoDefaultBody({})) == ""


def test_data_records_preserve_not_found_and_missing_data_contract() -> None:
    """Shared abuse.ch response gate should own not-found and missing-data behavior."""
    record = {"sha256_hash": "a" * 64}

    assert abusech_data_records(
        {"query_status": "hash_not_found", "data": [record]},
        no_data_status="hash_not_found",
    ) is None
    assert abusech_data_records(
        NoDefaultBody({"query_status": "ok"}),
        no_data_status="hash_not_found",
    ) is None
    assert abusech_data_records(
        {"query_status": "ok", "data": [record]},
        no_data_status="hash_not_found",
    ) == [record]


def test_data_records_preserve_no_result_and_missing_data_contract() -> None:
    """Shared abuse.ch response gate should own no-result and missing-data behavior."""
    record = {"confidence_level": 90}

    assert abusech_data_records(
        {"query_status": "no_result", "data": [record]},
        no_data_status="no_result",
    ) is None
    assert abusech_data_records(
        NoDefaultBody({"query_status": "ok"}),
        no_data_status="no_result",
    ) is None
    assert abusech_data_records(
        {"query_status": "ok", "data": [record]},
        no_data_status="no_result",
    ) == [record]


def test_data_records_delegate_query_status_fallback() -> None:
    """The data-list gate should use the shared abuse.ch query-status helper."""
    helper_source = inspect.getsource(abusech_data_records)

    assert "abusech_query_status(body)" in helper_source
    assert 'body.get("query_status"' not in helper_source
