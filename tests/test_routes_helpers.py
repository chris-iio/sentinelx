"""Compatibility wrapper for helper-route verification.

The S01 task plan referenced this filename, but helper status coverage lives in
``tests/test_routes.py`` after the routes package consolidation. Re-export the
relevant polling-route tests so the planned verification command remains valid.
"""

from tests.test_routes import (
    test_enrichment_error_serialization,
    test_enrichment_result_serialization,
    test_enrichment_status_evicted_job_returns_terminal_payload,
    test_enrichment_status_no_since_returns_all,
    test_enrichment_status_returns_json,
    test_enrichment_status_since_beyond_length,
    test_enrichment_status_since_returns_slice,
    test_enrichment_status_since_zero_returns_all,
    test_enrichment_status_unknown_job,
)

__all__ = [
    "test_enrichment_status_unknown_job",
    "test_enrichment_status_returns_json",
    "test_enrichment_result_serialization",
    "test_enrichment_error_serialization",
    "test_enrichment_status_evicted_job_returns_terminal_payload",
    "test_enrichment_status_since_returns_slice",
    "test_enrichment_status_since_zero_returns_all",
    "test_enrichment_status_no_since_returns_all",
    "test_enrichment_status_since_beyond_length",
]
