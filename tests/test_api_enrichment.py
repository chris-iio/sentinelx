"""Compatibility wrapper for slice-plan enrichment API verification.

The S01 plan referenced this filename, but the live backend coverage now lives in
``tests/test_api.py`` and ``tests/test_routes.py``. Re-export the relevant tests so
plan-driven verification commands continue to exercise the real status contract.
"""

from tests.test_api import TestApiStatus
from tests.test_routes import (
    test_enrichment_status_evicted_job_returns_terminal_payload,
    test_enrichment_status_no_since_returns_all,
    test_enrichment_status_since_beyond_length,
    test_enrichment_status_since_returns_slice,
    test_enrichment_status_since_zero_returns_all,
    test_enrichment_status_unknown_job,
)

__all__ = [
    "TestApiStatus",
    "test_enrichment_status_unknown_job",
    "test_enrichment_status_evicted_job_returns_terminal_payload",
    "test_enrichment_status_since_returns_slice",
    "test_enrichment_status_since_zero_returns_all",
    "test_enrichment_status_no_since_returns_all",
    "test_enrichment_status_since_beyond_length",
]
