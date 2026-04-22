"""Compatibility wrapper for slice-plan analysis-page verification.

The S01 plan referenced this filename, while the executable page-route coverage now
lives in ``tests/test_routes.py``. Re-export the online/offline analysis page tests
that prove the real analyst workflow still renders and starts enrichment correctly.
"""

from tests.test_routes import (
    test_analyze_offline_unchanged,
    test_analyze_online_with_api_key_returns_job_id,
    test_analyze_online_without_api_key_redirects_follows,
)

__all__ = [
    "test_analyze_online_with_api_key_returns_job_id",
    "test_analyze_online_without_api_key_redirects_follows",
    "test_analyze_offline_unchanged",
]
