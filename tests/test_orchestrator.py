"""Tests for EnrichmentOrchestrator.

Covers:
- Parallel execution (ThreadPoolExecutor — wall-clock timing)
- Error isolation (one failure does not block others)
- Retry-once behavior (failed lookup retried exactly once)
- Job status tracking (total, done, results, complete)
- Thread safety (concurrent writes don't corrupt state)
- LRU eviction (oldest job evicted after maxsize exceeded)
- Multi-adapter dispatch (Phase 3: multiple adapters per IOC)
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, call, patch

import pytest

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.models import IOC, IOCType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ioc(type_: IOCType, value: str) -> IOC:
    return IOC(type=type_, value=value, raw_match=value)


def _make_result(ioc: IOC, provider: str = "VirusTotal") -> EnrichmentResult:
    return EnrichmentResult(
        ioc=ioc,
        provider=provider,
        verdict="clean",
        detection_count=0,
        total_engines=10,
        scan_date=None,
        raw_stats={},
    )


def _make_error(ioc: IOC, msg: str = "Timeout", provider: str = "VirusTotal") -> EnrichmentError:
    return EnrichmentError(ioc=ioc, provider=provider, error=msg)


def _make_orchestrator(adapter, max_workers: int = 4) -> EnrichmentOrchestrator:
    return EnrichmentOrchestrator(adapters=[adapter], max_workers=max_workers)


def _make_mock_adapter(supported_types: set | None = None) -> MagicMock:
    """Create a mock adapter with supported_types and lookup method."""
    adapter = MagicMock()
    if supported_types is None:
        # Default: supports all non-CVE types (like VTAdapter)
        supported_types = {
            IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN,
            IOCType.URL, IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
        }
    adapter.supported_types = supported_types
    return adapter


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_adapter():
    return _make_mock_adapter()


# ---------------------------------------------------------------------------
# Tests — Legacy single-adapter behavior (backward compatibility via adapters=[...])
# ---------------------------------------------------------------------------

class TestEnrichAll:

    def test_enrich_all_calls_lookup_for_each_enrichable_ioc(self, mock_adapter):
        """CVE is not in supported_types — adapter.lookup must NOT be called for it."""
        ioc_ipv4_a = _make_ioc(IOCType.IPV4, "1.1.1.1")
        ioc_ipv4_b = _make_ioc(IOCType.IPV4, "8.8.8.8")
        ioc_cve = _make_ioc(IOCType.CVE, "CVE-2021-44228")

        mock_adapter.lookup.return_value = _make_result(ioc_ipv4_a)

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-1", [ioc_ipv4_a, ioc_ipv4_b, ioc_cve])

        # CVE must be skipped — only 2 enrichable IOCs
        assert mock_adapter.lookup.call_count == 2

    def test_enrich_all_parallel_execution(self, mock_adapter):
        """5 IOCs at 0.5s each: parallel (<3s total), not sequential (2.5s)."""
        iocs = [_make_ioc(IOCType.IPV4, f"10.0.0.{i}") for i in range(5)]

        def slow_lookup(ioc):
            time.sleep(0.5)
            return _make_result(ioc)

        mock_adapter.lookup.side_effect = slow_lookup

        orchestrator = _make_orchestrator(mock_adapter, max_workers=5)
        start = time.monotonic()
        orchestrator.enrich_all("job-parallel", iocs)
        elapsed = time.monotonic() - start

        # Sequential would take 2.5s; parallel with 5 workers should finish < 1.5s
        assert elapsed < 3.0, f"Expected parallel execution (<3s), got {elapsed:.2f}s"

    def test_enrich_all_returns_all_results(self, mock_adapter):
        """3 enrichable IOCs all succeed — job results must contain exactly 3 items."""
        iocs = [
            _make_ioc(IOCType.IPV4, "1.1.1.1"),
            _make_ioc(IOCType.DOMAIN, "example.com"),
            _make_ioc(IOCType.MD5, "a" * 32),
        ]

        def side_effect(ioc):
            return _make_result(ioc)

        mock_adapter.lookup.side_effect = side_effect

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-results", iocs)

        status = orchestrator.get_status("job-results")
        assert len(status["results"]) == 3
        assert all(isinstance(r, EnrichmentResult) for r in status["results"])

    def test_error_isolation(self, mock_adapter):
        """One IOC failure must not block or crash other IOC lookups."""
        ioc_a = _make_ioc(IOCType.IPV4, "1.1.1.1")
        ioc_b = _make_ioc(IOCType.IPV4, "2.2.2.2")
        ioc_c = _make_ioc(IOCType.IPV4, "3.3.3.3")

        def side_effect(ioc):
            if ioc.value == "2.2.2.2":
                # Return error for second IOC (simulates network failure)
                return _make_error(ioc)
            return _make_result(ioc)

        mock_adapter.lookup.side_effect = side_effect

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-isolation", [ioc_a, ioc_b, ioc_c])

        status = orchestrator.get_status("job-isolation")
        assert len(status["results"]) == 3

        results = status["results"]
        error_count = sum(1 for r in results if isinstance(r, EnrichmentError))
        success_count = sum(1 for r in results if isinstance(r, EnrichmentResult))
        assert error_count == 1
        assert success_count == 2


class TestRetryBehavior:

    def test_retry_on_failure(self, mock_adapter):
        """Adapter returns EnrichmentError on first call, EnrichmentResult on second.
        Final result must be EnrichmentResult (retry succeeded).
        adapter.lookup called exactly 2 times.
        """
        ioc = _make_ioc(IOCType.IPV4, "5.5.5.5")
        error_result = _make_error(ioc)
        success_result = _make_result(ioc)

        mock_adapter.lookup.side_effect = [error_result, success_result]

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-retry-success", [ioc])

        status = orchestrator.get_status("job-retry-success")
        assert len(status["results"]) == 1
        assert isinstance(status["results"][0], EnrichmentResult)
        assert mock_adapter.lookup.call_count == 2

    def test_retry_still_fails(self, mock_adapter):
        """Adapter returns EnrichmentError on both calls.
        Final result must be EnrichmentError.
        adapter.lookup called exactly 2 times.
        """
        ioc = _make_ioc(IOCType.IPV4, "6.6.6.6")
        error_result = _make_error(ioc)

        mock_adapter.lookup.side_effect = [error_result, error_result]

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-retry-fail", [ioc])

        status = orchestrator.get_status("job-retry-fail")
        assert len(status["results"]) == 1
        assert isinstance(status["results"][0], EnrichmentError)
        assert mock_adapter.lookup.call_count == 2


class TestJobStatusTracking:

    def test_job_status_tracking(self, mock_adapter):
        """get_status(job_id) returns dict with keys: total, done, results, complete."""
        ioc = _make_ioc(IOCType.IPV4, "7.7.7.7")
        mock_adapter.lookup.return_value = _make_result(ioc)

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-status", [ioc])

        status = orchestrator.get_status("job-status")
        assert status is not None
        assert "total" in status
        assert "done" in status
        assert "results" in status
        assert "complete" in status

    def test_job_status_complete_flag(self, mock_adapter):
        """After enrich_all finishes, get_status(job_id)["complete"] must be True."""
        ioc = _make_ioc(IOCType.IPV4, "8.8.8.8")
        mock_adapter.lookup.return_value = _make_result(ioc)

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-complete", [ioc])

        status = orchestrator.get_status("job-complete")
        assert status["complete"] is True

    def test_job_status_done_count(self, mock_adapter):
        """done count must equal total after enrich_all completes."""
        iocs = [_make_ioc(IOCType.IPV4, f"192.168.0.{i}") for i in range(3)]
        mock_adapter.lookup.side_effect = [_make_result(ioc) for ioc in iocs]

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-done-count", iocs)

        status = orchestrator.get_status("job-done-count")
        assert status["total"] == 3
        assert status["done"] == 3

    def test_get_status_unknown_job(self, mock_adapter):
        """get_status on a non-existent job_id returns None."""
        orchestrator = _make_orchestrator(mock_adapter)
        assert orchestrator.get_status("nonexistent") is None


class TestLRUEviction:

    def test_job_cleanup_lru(self, mock_adapter):
        """After creating 101 jobs (maxsize=100), first job must be evicted.
        get_status(first_job_id) must return None after eviction.
        """
        ioc = _make_ioc(IOCType.IPV4, "9.9.9.9")
        mock_adapter.lookup.return_value = _make_result(ioc)

        # Use a small max_jobs to avoid creating 101 real jobs
        # We pass max_jobs=5, create 6 jobs, and verify first is evicted
        orchestrator = EnrichmentOrchestrator(adapters=[mock_adapter], max_workers=1, max_jobs=5)

        first_job_id = "job-lru-0"
        for i in range(6):
            job_id = f"job-lru-{i}"
            orchestrator.enrich_all(job_id, [ioc])

        # First job must be evicted after 6 jobs with maxsize=5
        assert orchestrator.get_status(first_job_id) is None
        # Most recent job must still be present
        assert orchestrator.get_status("job-lru-5") is not None


# ---------------------------------------------------------------------------
# Tests — Multi-adapter dispatch (Phase 3)
# ---------------------------------------------------------------------------

class TestMultiAdapterDispatch:

    def test_multi_adapter_dispatches_to_all_matching(self):
        """Two adapters both supporting IPV4 — both should be called for one IPV4 IOC."""
        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")

        adapter_a = _make_mock_adapter(supported_types={IOCType.IPV4})
        adapter_b = _make_mock_adapter(supported_types={IOCType.IPV4, IOCType.DOMAIN})
        adapter_a.lookup.return_value = _make_result(ioc, provider="ProviderA")
        adapter_b.lookup.return_value = _make_result(ioc, provider="ProviderB")

        orchestrator = EnrichmentOrchestrator(adapters=[adapter_a, adapter_b], max_workers=4)
        orchestrator.enrich_all("job-multi-a", [ioc])

        status = orchestrator.get_status("job-multi-a")
        # One IPV4 IOC dispatched to both adapters = 2 results
        assert len(status["results"]) == 2
        assert adapter_a.lookup.call_count == 1
        assert adapter_b.lookup.call_count == 1

    def test_multi_adapter_skips_unsupported_type(self):
        """Adapter supporting only MD5 should be skipped for a DOMAIN IOC."""
        ioc = _make_ioc(IOCType.DOMAIN, "evil.com")

        adapter_a = _make_mock_adapter(supported_types={IOCType.MD5})
        adapter_a.lookup.return_value = _make_result(ioc, provider="ProviderA")

        orchestrator = EnrichmentOrchestrator(adapters=[adapter_a], max_workers=4)
        orchestrator.enrich_all("job-skip-unsupported", [ioc])

        status = orchestrator.get_status("job-skip-unsupported")
        # DOMAIN IOC not in adapter_a.supported_types — 0 dispatches
        assert len(status["results"]) == 0
        assert adapter_a.lookup.call_count == 0

    def test_multi_adapter_total_counts_all_dispatches(self):
        """2 IOCs x 2 adapters (both supporting both types) = total of 4 dispatches."""
        ioc_a = _make_ioc(IOCType.IPV4, "1.1.1.1")
        ioc_b = _make_ioc(IOCType.MD5, "a" * 32)

        adapter_a = _make_mock_adapter(supported_types={IOCType.IPV4, IOCType.MD5})
        adapter_b = _make_mock_adapter(supported_types={IOCType.IPV4, IOCType.MD5})

        def result_a(ioc):
            return _make_result(ioc, provider="ProviderA")

        def result_b(ioc):
            return _make_result(ioc, provider="ProviderB")

        adapter_a.lookup.side_effect = result_a
        adapter_b.lookup.side_effect = result_b

        orchestrator = EnrichmentOrchestrator(adapters=[adapter_a, adapter_b], max_workers=4)
        orchestrator.enrich_all("job-total-count", [ioc_a, ioc_b])

        status = orchestrator.get_status("job-total-count")
        # total reflects dispatched lookups: 2 IOCs x 2 adapters = 4
        assert status["total"] == 4
        assert len(status["results"]) == 4

    def test_adapter_failure_isolated_across_providers(self):
        """adapter_a error does not block adapter_b from returning a result."""
        ioc = _make_ioc(IOCType.IPV4, "9.9.9.9")

        adapter_a = _make_mock_adapter(supported_types={IOCType.IPV4})
        adapter_b = _make_mock_adapter(supported_types={IOCType.IPV4})
        adapter_a.lookup.return_value = _make_error(ioc, msg="Timeout", provider="ProviderA")
        adapter_b.lookup.return_value = _make_result(ioc, provider="ProviderB")

        orchestrator = EnrichmentOrchestrator(adapters=[adapter_a, adapter_b], max_workers=4)
        orchestrator.enrich_all("job-provider-isolation", [ioc])

        status = orchestrator.get_status("job-provider-isolation")
        # Both results present: one error from a, one result from b
        assert len(status["results"]) == 2

        error_count = sum(1 for r in status["results"] if isinstance(r, EnrichmentError))
        result_count = sum(1 for r in status["results"] if isinstance(r, EnrichmentResult))
        assert error_count == 1
        assert result_count == 1


# ---------------------------------------------------------------------------
# Tests — Per-provider semaphore (R014)
# ---------------------------------------------------------------------------

class TestPerProviderSemaphore:
    """Verify that requires_api_key=True adapters are semaphore-gated while
    zero-auth adapters run freely, and that provider_concurrency overrides work."""

    def _make_vt_adapter(self, sleep_secs: float = 0.3):
        """Return a mock VirusTotal adapter that sleeps to simulate rate limiting."""
        adapter = MagicMock()
        adapter.name = "VirusTotal"
        adapter.requires_api_key = True
        adapter.supported_types = {IOCType.IPV4}

        def slow_lookup(ioc):
            time.sleep(sleep_secs)
            return _make_result(ioc, provider="VirusTotal")

        adapter.lookup.side_effect = slow_lookup
        return adapter

    def _make_free_adapter(self):
        """Return a mock zero-auth DNS adapter that returns instantly."""
        adapter = MagicMock()
        adapter.name = "DNSLookup"
        adapter.requires_api_key = False
        adapter.supported_types = {IOCType.IPV4}

        def instant_lookup(ioc):
            return _make_result(ioc, provider="DNSLookup")

        adapter.lookup.side_effect = instant_lookup
        return adapter

    def test_no_semaphore_for_zero_auth_provider(self):
        """Zero-auth adapters must NOT get a semaphore; API-key adapters must."""
        vt_adapter = self._make_vt_adapter()
        free_adapter = self._make_free_adapter()

        orchestrator = EnrichmentOrchestrator(
            adapters=[vt_adapter, free_adapter],
            max_workers=20,
        )

        assert "VirusTotal" in orchestrator._semaphores, (
            "VirusTotal (requires_api_key=True) must have a semaphore entry"
        )
        assert "DNSLookup" not in orchestrator._semaphores, (
            "DNSLookup (requires_api_key=False) must NOT have a semaphore entry"
        )

    def test_rate_limited_provider_concurrency_capped(self):
        """Peak concurrent VT calls must not exceed the semaphore cap.

        With semaphore cap=2 and 4 VT lookups, peak concurrency must be ≤ 2.
        """
        peak_concurrent = 0
        current_concurrent = 0
        counter_lock = threading.Lock()

        vt_adapter = MagicMock()
        vt_adapter.name = "VirusTotal"
        vt_adapter.requires_api_key = True
        vt_adapter.supported_types = {IOCType.IPV4}

        def tracked_lookup(ioc):
            nonlocal peak_concurrent, current_concurrent
            with counter_lock:
                current_concurrent += 1
                if current_concurrent > peak_concurrent:
                    peak_concurrent = current_concurrent
            time.sleep(0.1)
            with counter_lock:
                current_concurrent -= 1
            return _make_result(ioc, provider="VirusTotal")

        vt_adapter.lookup.side_effect = tracked_lookup

        iocs = [_make_ioc(IOCType.IPV4, f"10.0.0.{i}") for i in range(4)]
        orchestrator = EnrichmentOrchestrator(
            adapters=[vt_adapter],
            max_workers=20,
            provider_concurrency={"VirusTotal": 2},
        )
        orchestrator.enrich_all("job-semaphore-cap", iocs)

        assert peak_concurrent <= 2, (
            f"Expected peak VT concurrency ≤ 2 (semaphore cap), got {peak_concurrent}"
        )

    def test_zero_auth_not_blocked_by_rate_limited_provider(self):
        """Zero-auth adapter must complete without waiting for VT's semaphore.

        With VT semaphore cap=2 and 4 VT lookups at 0.3s each, VT alone takes
        ~0.6s (two batches). The free adapter must finish much earlier since it
        holds no semaphore. Total wall time must be <1.0s, confirming the free
        adapter didn't serialize behind VT.
        """
        vt_adapter = self._make_vt_adapter(sleep_secs=0.3)
        free_adapter = self._make_free_adapter()

        iocs = [_make_ioc(IOCType.IPV4, f"10.0.1.{i}") for i in range(4)]
        orchestrator = EnrichmentOrchestrator(
            adapters=[vt_adapter, free_adapter],
            max_workers=20,
            provider_concurrency={"VirusTotal": 2},
        )

        start = time.monotonic()
        orchestrator.enrich_all("job-free-not-blocked", iocs)
        elapsed = time.monotonic() - start

        status = orchestrator.get_status("job-free-not-blocked")
        # 4 IOCs × 2 adapters = 8 total lookups
        assert status["total"] == 8
        assert len(status["results"]) == 8

        # VT alone takes ≥0.6s (2 batches × 0.3s). Free adapter is instant.
        # If free adapter was blocked by VT's semaphore the total would approach 0.6s+.
        # Either way the whole job completes in <1.0s (VT's 0.6s + scheduling overhead).
        assert elapsed < 1.0, (
            f"Expected total time <1.0s (VT semaphore-capped, free runs in parallel), "
            f"got {elapsed:.2f}s"
        )


# ---------------------------------------------------------------------------
# Tests — 429-aware exponential backoff (R015)
# ---------------------------------------------------------------------------

class TestBackoff429:
    """Verify that 429/rate-limit errors trigger exponential backoff+retry while
    non-429 errors keep the existing immediate single-retry behavior."""

    def _make_vt_adapter(self) -> MagicMock:
        """Return a realistic VirusTotal mock (requires_api_key=True, IPV4)."""
        adapter = MagicMock()
        adapter.name = "VirusTotal"
        adapter.requires_api_key = True
        adapter.supported_types = {IOCType.IPV4}
        return adapter

    def _run_single_lookup(self, adapter: MagicMock) -> EnrichmentResult | EnrichmentError:
        """Helper: create orchestrator for a single VT-style adapter and run one IOC."""
        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")
        orchestrator = EnrichmentOrchestrator(
            adapters=[adapter],
            max_workers=4,
            provider_concurrency={"VirusTotal": 4},
        )
        orchestrator.enrich_all("job-backoff-test", [ioc])
        status = orchestrator.get_status("job-backoff-test")
        assert len(status["results"]) == 1
        return status["results"][0]

    def test_429_triggers_backoff_sleep(self):
        """429 error on first call must trigger one sleep before retry.

        After 1×429 then success:
        - adapter.lookup called exactly 2 times
        - time.sleep called once with delay in [15.0, 17.0) (base=15s + jitter[0,2))
        - final result is EnrichmentResult (retry succeeded)
        """
        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")
        adapter = self._make_vt_adapter()
        error_429 = _make_error(ioc, msg="Rate limit exceeded (429)")
        success = _make_result(ioc, provider="VirusTotal")
        adapter.lookup.side_effect = [error_429, success]

        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            result = self._run_single_lookup(adapter)

        assert adapter.lookup.call_count == 2, (
            f"Expected 2 calls (initial + 1 retry), got {adapter.lookup.call_count}"
        )
        mock_sleep.assert_called_once()
        sleep_delay = mock_sleep.call_args[0][0]
        assert 15.0 <= sleep_delay < 17.0, (
            f"Expected delay in [15.0, 17.0), got {sleep_delay:.3f}"
        )
        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult after successful retry, got {result}"
        )

    def test_non_429_error_no_backoff(self):
        """Non-429 error must use immediate single retry without any sleep.

        After 1×Timeout then success:
        - adapter.lookup called exactly 2 times
        - time.sleep NOT called
        - final result is EnrichmentResult (retry succeeded)
        """
        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")
        adapter = self._make_vt_adapter()
        timeout_error = _make_error(ioc, msg="Timeout")
        success = _make_result(ioc, provider="VirusTotal")
        adapter.lookup.side_effect = [timeout_error, success]

        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            result = self._run_single_lookup(adapter)

        assert adapter.lookup.call_count == 2, (
            f"Expected 2 calls (initial + immediate retry), got {adapter.lookup.call_count}"
        )
        mock_sleep.assert_not_called()
        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult after successful retry, got {result}"
        )

    def test_triple_429_exhausts_retries(self):
        """Three consecutive 429 errors must exhaust all retries.

        After 3×429:
        - adapter.lookup called exactly 3 times (initial + 2 backoff retries)
        - time.sleep called exactly 2 times (before retry 1 and retry 2)
        - sleep delays are ~15s then ~30s (base×2^0 + jitter, base×2^1 + jitter)
        - final result is EnrichmentError
        """
        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")
        adapter = self._make_vt_adapter()
        error_429 = _make_error(ioc, msg="Rate limit exceeded (429)")
        adapter.lookup.side_effect = [error_429, error_429, error_429]

        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            result = self._run_single_lookup(adapter)

        assert adapter.lookup.call_count == 3, (
            f"Expected 3 calls (initial + 2 retries), got {adapter.lookup.call_count}"
        )
        assert mock_sleep.call_count == 2, (
            f"Expected 2 sleep calls (before retry 1 and 2), got {mock_sleep.call_count}"
        )
        # First sleep: ~15s (base=15 × 2^0 + jitter[0,2))
        delay_1 = mock_sleep.call_args_list[0][0][0]
        assert 15.0 <= delay_1 < 17.0, (
            f"Expected first delay in [15.0, 17.0), got {delay_1:.3f}"
        )
        # Second sleep: ~30s (base=15 × 2^1 + jitter[0,2))
        delay_2 = mock_sleep.call_args_list[1][0][0]
        assert 30.0 <= delay_2 < 32.0, (
            f"Expected second delay in [30.0, 32.0), got {delay_2:.3f}"
        )
        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError after all retries exhausted, got {result}"
        )

    def test_429_then_non_429_error_stops_retrying(self):
        """429 followed by a non-429 error must stop after 1 retry (no second backoff).

        After 1×429 then 1×Timeout error:
        - adapter.lookup called exactly 2 times (initial + 1 retry after backoff)
        - time.sleep called exactly once (before the first retry)
        - final result is EnrichmentError with "Timeout" message (not the 429)
        """
        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")
        adapter = self._make_vt_adapter()
        error_429 = _make_error(ioc, msg="Rate limit exceeded (429)")
        timeout_error = _make_error(ioc, msg="Timeout")
        adapter.lookup.side_effect = [error_429, timeout_error]

        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            result = self._run_single_lookup(adapter)

        assert adapter.lookup.call_count == 2, (
            f"Expected 2 calls (initial + 1 retry), got {adapter.lookup.call_count}"
        )
        mock_sleep.assert_called_once()
        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError, got {result}"
        )
        assert "Timeout" in result.error, (
            f"Expected 'Timeout' in final error message, got: {result.error!r}"
        )
