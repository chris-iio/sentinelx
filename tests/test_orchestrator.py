"""Tests for EnrichmentOrchestrator.

Covers:
- Parallel execution (ThreadPoolExecutor — wall-clock timing)
- Error isolation (one failure does not block others)
- Retry-once behavior (failed lookup retried exactly once)
- Job status tracking (total, done, results, complete)
- Thread safety (concurrent writes don't corrupt state)
- LRU eviction (oldest job evicted after maxsize exceeded)
- Multi-adapter dispatch (Phase 3: multiple adapters per IOC)
- Per-provider semaphore (M003 S01: VT capped at ≤4, zero-auth runs freely)
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    _BACKOFF_BASE,
    _MAX_RATE_LIMIT_RETRIES,
)
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
        """5 IOCs dispatched in parallel — barrier proves all 5 threads run concurrently."""
        iocs = [_make_ioc(IOCType.IPV4, f"10.0.0.{i}") for i in range(5)]
        barrier = threading.Barrier(5, timeout=2)

        def barrier_lookup(ioc):
            barrier.wait()  # blocks until all 5 threads arrive
            return _make_result(ioc)

        mock_adapter.lookup.side_effect = barrier_lookup
        mock_adapter.requires_api_key = False  # no semaphore gating

        orchestrator = _make_orchestrator(mock_adapter, max_workers=5)
        with patch("app.enrichment.orchestrator.time.sleep"):
            orchestrator.enrich_all("job-parallel", iocs)

        status = orchestrator.get_status("job-parallel")
        assert len(status["results"]) == 5
        # If barrier.wait() didn't timeout, all 5 threads were concurrent

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
        with patch("app.enrichment.orchestrator.time.sleep"):
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
        with patch("app.enrichment.orchestrator.time.sleep"):
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
        with patch("app.enrichment.orchestrator.time.sleep"):
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
        with patch("app.enrichment.orchestrator.time.sleep"):
            orchestrator.enrich_all("job-provider-isolation", [ioc])

            status = orchestrator.get_status("job-provider-isolation")
            # Both results present: one error from a, one result from b
            assert len(status["results"]) == 2

            error_count = sum(1 for r in status["results"] if isinstance(r, EnrichmentError))
            result_count = sum(1 for r in status["results"] if isinstance(r, EnrichmentResult))
            assert error_count == 1
            assert result_count == 1


# ---------------------------------------------------------------------------
# Tests — Per-provider semaphore (M003 S01 T01)
# ---------------------------------------------------------------------------

def _make_keyed_adapter(name: str, supported_types: set | None = None) -> MagicMock:
    """Create a mock adapter that requires an API key (for semaphore gating)."""
    adapter = _make_mock_adapter(supported_types)
    adapter.name = name
    adapter.requires_api_key = True
    return adapter


def _make_public_adapter(name: str, supported_types: set | None = None) -> MagicMock:
    """Create a mock adapter that does NOT require an API key (no semaphore)."""
    adapter = _make_mock_adapter(supported_types)
    adapter.name = name
    adapter.requires_api_key = False
    return adapter


class TestPerProviderSemaphore:
    """Prove that per-provider semaphores cap rate-limited providers independently.

    These tests verify that:
    - VT (requires_api_key=True) is capped at ≤4 concurrent lookups
    - Zero-auth providers complete without waiting for VT slots
    - No semaphore is built for adapters without requires_api_key
    """

    def test_vt_peak_concurrency_capped_at_4(self):
        """8 IOCs with a VT adapter — peak concurrent VT lookups must stay ≤ 4.

        Uses a shared counter + Lock to track peak concurrent VT invocations.
        The orchestrator is given max_workers=20 so the thread pool is not the gate;
        only the semaphore should cap concurrency.
        """
        peak_vt = 0
        current_vt = 0
        vt_lock = threading.Lock()
        batch_full = threading.Event()

        iocs = [_make_ioc(IOCType.IPV4, f"10.0.0.{i}") for i in range(8)]

        vt_adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})

        def coordinated_vt_lookup(ioc):
            nonlocal peak_vt, current_vt
            with vt_lock:
                current_vt += 1
                peak_vt = max(peak_vt, current_vt)
                if current_vt >= 4:
                    batch_full.set()
            batch_full.wait(timeout=2)  # hold threads until batch measured
            with vt_lock:
                current_vt -= 1
            return _make_result(ioc, provider="VirusTotal")

        vt_adapter.lookup.side_effect = coordinated_vt_lookup

        orchestrator = EnrichmentOrchestrator(adapters=[vt_adapter], max_workers=20)
        with patch("app.enrichment.orchestrator.time.sleep"):
            orchestrator.enrich_all("job-semaphore-cap", iocs)

        status = orchestrator.get_status("job-semaphore-cap")
        assert len(status["results"]) == 8
        assert peak_vt <= 4, f"VT peak concurrency {peak_vt} exceeded semaphore cap of 4"

    def test_zero_auth_completes_without_waiting_for_vt(self):
        """Zero-auth adapter (no semaphore) finishes all lookups alongside VT.

        VT uses an Event.wait with near-instant timeout (no real delay).
        DNS is instant. All 16 results (8 VT + 8 DNS) must be present,
        and DNS must have completed all 8 calls.
        """
        iocs = [_make_ioc(IOCType.IPV4, f"10.0.1.{i}") for i in range(8)]

        vt_adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})
        dns_adapter = _make_public_adapter("DNS", supported_types={IOCType.IPV4})
        dns_call_count = threading.Event()
        dns_calls = [0]
        dns_lock = threading.Lock()

        vt_gate = threading.Event()  # never set — expires near-instantly

        def gated_vt_lookup(ioc):
            vt_gate.wait(timeout=0.01)  # near-instant expiry, no real delay
            return _make_result(ioc, provider="VirusTotal")

        def instant_dns_lookup(ioc):
            with dns_lock:
                dns_calls[0] += 1
                if dns_calls[0] == 8:
                    dns_call_count.set()
            return _make_result(ioc, provider="DNS")

        vt_adapter.lookup.side_effect = gated_vt_lookup
        dns_adapter.lookup.side_effect = instant_dns_lookup

        orchestrator = EnrichmentOrchestrator(
            adapters=[vt_adapter, dns_adapter], max_workers=20
        )
        with patch("app.enrichment.orchestrator.time.sleep"):
            orchestrator.enrich_all("job-dns-free", iocs)

        status = orchestrator.get_status("job-dns-free")
        # All 16 results must be present (8 VT + 8 DNS)
        assert len(status["results"]) == 16, (
            f"Expected 16 results (8 VT + 8 DNS), got {len(status['results'])}"
        )
        # DNS must have completed all 8 calls (event was set)
        assert dns_call_count.is_set(), "DNS adapter did not complete all 8 lookups"
        # Verify DNS adapter was called 8 times
        assert dns_adapter.lookup.call_count == 8

    def test_semaphore_built_only_for_keyed_adapters(self):
        """Only adapters with requires_api_key=True get a semaphore entry.

        An orchestrator with one public adapter should have an empty _semaphores dict.
        An orchestrator with one keyed adapter should have exactly one semaphore.
        """
        public_adapter = _make_public_adapter("Shodan", supported_types={IOCType.IPV4})
        keyed_adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})

        orch_public = EnrichmentOrchestrator(adapters=[public_adapter])
        orch_keyed = EnrichmentOrchestrator(adapters=[keyed_adapter])
        orch_mixed = EnrichmentOrchestrator(adapters=[public_adapter, keyed_adapter])

        assert len(orch_public._semaphores) == 0, "Public adapter must not get a semaphore"
        assert len(orch_keyed._semaphores) == 1, "Keyed adapter must get exactly one semaphore"
        assert "VirusTotal" in orch_keyed._semaphores
        assert len(orch_mixed._semaphores) == 1, "Mixed: only keyed adapter gets semaphore"

    def test_provider_concurrency_override(self):
        """provider_concurrency dict overrides the default cap of 4.

        Orchestrator created with provider_concurrency={"VirusTotal": 2} should have
        a semaphore with internal value 2, not the default 4.
        """
        keyed_adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})

        orch_default = EnrichmentOrchestrator(adapters=[keyed_adapter])
        orch_custom = EnrichmentOrchestrator(
            adapters=[keyed_adapter], provider_concurrency={"VirusTotal": 2}
        )

        # Verify both have a VT semaphore
        assert "VirusTotal" in orch_default._semaphores
        assert "VirusTotal" in orch_custom._semaphores

        # The default semaphore should allow 4 acquires without blocking;
        # the custom one should block after 2. We verify via _value attribute
        # (CPython implementation detail — Semaphore._value is the internal counter).
        default_sem = orch_default._semaphores["VirusTotal"]
        custom_sem = orch_custom._semaphores["VirusTotal"]
        assert default_sem._value == 4, f"Default cap should be 4, got {default_sem._value}"
        assert custom_sem._value == 2, f"Custom cap should be 2, got {custom_sem._value}"


# ---------------------------------------------------------------------------
# Tests — 429-aware exponential backoff (M003 S01 T02)
# ---------------------------------------------------------------------------


def _make_vt_adapter() -> MagicMock:
    """Create a keyed VT-style adapter (requires_api_key=True) for backoff tests."""
    adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})
    return adapter


class TestBackoff429:
    """Prove that 429 rate-limit errors trigger exponential backoff, not immediate retry.

    These tests verify that:
    - 429/rate-limit errors cause time.sleep() calls before retrying
    - Non-429 errors do NOT trigger time.sleep() (immediate retry preserved)
    - All retries exhaust correctly (3 total attempts for 429)
    - Delay values increase exponentially across successive retries
    - Both "429" numeric and "rate limit" string variants trigger backoff
    """

    def test_429_triggers_backoff_sleep(self):
        """Adapter returns 429 error on first call, EnrichmentResult on second.

        Expects:
        - time.sleep called at least once with delay ≥ _BACKOFF_BASE
        - Final result is EnrichmentResult (retry after backoff succeeded)
        - adapter.lookup called exactly 2 times (initial + 1 retry)
        """
        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")
        adapter = _make_vt_adapter()
        adapter.lookup.side_effect = [
            _make_error(ioc, msg="Rate limit exceeded (429)", provider="VirusTotal"),
            _make_result(ioc, provider="VirusTotal"),
        ]

        orchestrator = _make_orchestrator(adapter)
        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            orchestrator.enrich_all("job-429-sleep", [ioc])

        status = orchestrator.get_status("job-429-sleep")
        assert isinstance(status["results"][0], EnrichmentResult), (
            "Expected EnrichmentResult after retry, got EnrichmentError"
        )
        assert mock_sleep.call_count >= 1, "Expected time.sleep to be called for 429 backoff"
        sleep_arg = mock_sleep.call_args_list[0][0][0]
        assert sleep_arg >= _BACKOFF_BASE, (
            f"First backoff delay {sleep_arg:.1f}s must be ≥ base {_BACKOFF_BASE}s"
        )
        assert adapter.lookup.call_count == 2

    def test_non_429_retry_sleeps_1s(self):
        """Adapter returns generic Timeout error on first call, success on second.

        Expects:
        - time.sleep called exactly once with a 1s delay (new non-429 retry delay)
        - Final result is EnrichmentResult (retry succeeded)
        - adapter.lookup called exactly 2 times
        """
        ioc = _make_ioc(IOCType.IPV4, "2.3.4.5")
        adapter = _make_vt_adapter()
        adapter.lookup.side_effect = [
            _make_error(ioc, msg="Timeout", provider="VirusTotal"),
            _make_result(ioc, provider="VirusTotal"),
        ]

        orchestrator = _make_orchestrator(adapter)
        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            orchestrator.enrich_all("job-timeout-no-sleep", [ioc])

        status = orchestrator.get_status("job-timeout-no-sleep")
        assert isinstance(status["results"][0], EnrichmentResult), (
            "Expected EnrichmentResult after immediate retry"
        )
        assert mock_sleep.call_count == 1, (
            "Non-429 retry should sleep exactly once (1s delay)"
        )
        assert mock_sleep.call_args_list[0][0][0] == 1, (
            "Non-429 retry delay should be 1 second"
        )
        assert adapter.lookup.call_count == 2

    def test_triple_429_exhausts_retries(self):
        """Adapter returns HTTP 429 on all 3 calls — retries exhaust, final result is error.

        Expects:
        - time.sleep called exactly _MAX_RATE_LIMIT_RETRIES (2) times
        - Final result is EnrichmentError (all attempts failed)
        - adapter.lookup called exactly 3 times (1 initial + 2 retries)
        """
        ioc = _make_ioc(IOCType.IPV4, "3.4.5.6")
        adapter = _make_vt_adapter()
        error = _make_error(ioc, msg="HTTP 429", provider="VirusTotal")
        adapter.lookup.return_value = error  # all calls return 429

        orchestrator = _make_orchestrator(adapter)
        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            orchestrator.enrich_all("job-triple-429", [ioc])

        status = orchestrator.get_status("job-triple-429")
        assert isinstance(status["results"][0], EnrichmentError), (
            "Expected EnrichmentError after exhausting all 429 retries"
        )
        assert mock_sleep.call_count == _MAX_RATE_LIMIT_RETRIES, (
            f"Expected {_MAX_RATE_LIMIT_RETRIES} sleep calls for {_MAX_RATE_LIMIT_RETRIES} retries, "
            f"got {mock_sleep.call_count}"
        )
        assert adapter.lookup.call_count == 3, (
            f"Expected 3 total lookup calls (1 initial + {_MAX_RATE_LIMIT_RETRIES} retries), "
            f"got {adapter.lookup.call_count}"
        )

    def test_backoff_delays_increase_exponentially(self):
        """On successive 429 errors, each sleep delay must be greater than the previous.

        With base=15s, multiplier=2: attempt 1 ≈ 15s, attempt 2 ≈ 30s (+jitter).
        Asserts second sleep arg > first sleep arg.
        """
        ioc = _make_ioc(IOCType.IPV4, "4.5.6.7")
        adapter = _make_vt_adapter()
        error = _make_error(ioc, msg="HTTP 429", provider="VirusTotal")
        adapter.lookup.return_value = error

        orchestrator = _make_orchestrator(adapter)
        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            orchestrator.enrich_all("job-exp-backoff", [ioc])

        assert mock_sleep.call_count == _MAX_RATE_LIMIT_RETRIES, (
            f"Expected {_MAX_RATE_LIMIT_RETRIES} sleep calls, got {mock_sleep.call_count}"
        )
        delay_1 = mock_sleep.call_args_list[0][0][0]
        delay_2 = mock_sleep.call_args_list[1][0][0]
        assert delay_2 > delay_1, (
            f"Second delay ({delay_2:.1f}s) must exceed first delay ({delay_1:.1f}s) "
            "for exponential backoff"
        )

    def test_rate_limit_string_without_429_triggers_backoff(self):
        """'Rate limit exceeded' (no numeric 429) also triggers backoff sleep.

        Verifies that case-insensitive 'rate limit' substring match works
        independently of the numeric code.
        """
        ioc = _make_ioc(IOCType.IPV4, "5.6.7.8")
        adapter = _make_vt_adapter()
        adapter.lookup.side_effect = [
            _make_error(ioc, msg="Rate limit exceeded", provider="VirusTotal"),
            _make_result(ioc, provider="VirusTotal"),
        ]

        orchestrator = _make_orchestrator(adapter)
        with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
            orchestrator.enrich_all("job-ratelimit-string", [ioc])

        status = orchestrator.get_status("job-ratelimit-string")
        assert isinstance(status["results"][0], EnrichmentResult)
        assert mock_sleep.call_count >= 1, (
            "'Rate limit exceeded' (no 429 code) must still trigger backoff sleep"
        )


# ---------------------------------------------------------------------------
# Tests — M004 S01 concurrency correctness fixes
# ---------------------------------------------------------------------------


class TestSemaphoreReleasedDuringBackoff:
    """Prove that the semaphore is released before time.sleep() during 429 backoff.

    Before the fix, the semaphore was held for the entire retry cycle (including
    sleep), so all N slots slept simultaneously and starved every other queued IOC.
    After the fix, the semaphore is released before sleep so other threads can run.
    """

    def test_semaphore_released_during_backoff_sleep(self):
        """IOC-B should complete while IOC-A is sleeping after a 429.

        Uses threading.Event coordination:
        - IOC-A hits 429 → sets 'sleeping' event → (would) sleep
        - IOC-B waits for 'sleeping' event → acquires semaphore → completes
        - Assert IOC-B completed before mock_sleep returned (i.e. sem was released)

        With semaphore cap=1, if the sem were held during sleep, IOC-B would
        block waiting for IOC-A to wake up, and 'b_completed' would never be set.
        """
        sleeping_event = threading.Event()   # set when IOC-A is about to sleep
        b_completed_event = threading.Event()  # set when IOC-B finishes its lookup
        # We need to detect when IOC-B completes while the sleep mock is "sleeping"
        b_completed_before_sleep_returns = threading.Event()

        ioc_a = _make_ioc(IOCType.IPV4, "10.0.0.1")
        ioc_b = _make_ioc(IOCType.IPV4, "10.0.0.2")

        adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})
        result_a = _make_result(ioc_a, provider="VirusTotal")
        result_b = _make_result(ioc_b, provider="VirusTotal")

        error_429 = _make_error(ioc_a, msg="HTTP 429", provider="VirusTotal")

        call_count = {"a": 0, "b": 0}
        call_lock = threading.Lock()

        def side_effect(ioc):
            with call_lock:
                if ioc.value == ioc_a.value:
                    call_count["a"] += 1
                    if call_count["a"] == 1:
                        return error_429  # first call → 429
                    return result_a      # retry → success
                else:
                    call_count["b"] += 1
                    result = result_b
                    b_completed_event.set()
                    return result

        adapter.lookup.side_effect = side_effect

        # Orchestrator with cap=1 so the behaviour is maximal — if sem were held
        # during sleep, IOC-B could not proceed at all.
        orchestrator = EnrichmentOrchestrator(
            adapters=[adapter],
            max_workers=4,
            provider_concurrency={"VirusTotal": 1},
        )

        sleep_call_count = [0]

        def fake_sleep(duration):
            sleep_call_count[0] += 1
            if sleep_call_count[0] == 1:
                # Signal "about to sleep" — IOC-B can now try to acquire sem
                sleeping_event.set()
                # Wait briefly to give IOC-B a chance to acquire and complete
                b_completed_event.wait(timeout=2.0)
                if b_completed_event.is_set():
                    b_completed_before_sleep_returns.set()

        with patch("app.enrichment.orchestrator.time.sleep", side_effect=fake_sleep):
            orchestrator.enrich_all("job-sem-sleep", [ioc_a, ioc_b])

        status = orchestrator.get_status("job-sem-sleep")
        assert len(status["results"]) == 2, (
            f"Expected 2 results, got {len(status['results'])}"
        )
        assert b_completed_before_sleep_returns.is_set(), (
            "IOC-B should have completed while IOC-A was sleeping (semaphore was not released "
            "before sleep — bug still present)"
        )


class TestGetStatusListSnapshot:
    """Prove that get_status() returns a snapshot of results, not the live list."""

    def test_get_status_returns_list_snapshot(self):
        """Mutating the returned results list must not affect the internal job results.

        After enrich_all() completes:
        1. Get status → capture returned results list.
        2. Append a dummy item to the returned list.
        3. Get status again → internal results should be unchanged (original length).
        """
        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")
        adapter = _make_mock_adapter()
        adapter.lookup.return_value = _make_result(ioc)

        orchestrator = _make_orchestrator(adapter)
        orchestrator.enrich_all("job-snapshot", [ioc])

        status1 = orchestrator.get_status("job-snapshot")
        original_len = len(status1["results"])
        assert original_len == 1

        # Mutate the returned list
        dummy = _make_error(ioc, msg="dummy")
        status1["results"].append(dummy)

        # The internal job should be unaffected
        status2 = orchestrator.get_status("job-snapshot")
        assert len(status2["results"]) == original_len, (
            f"Internal results list was mutated: expected {original_len} items, "
            f"got {len(status2['results'])}. get_status() must return a list copy."
        )


class TestCachedMarkersLock:
    """Prove that _cached_markers reads and writes are protected by _lock."""

    def test_cached_markers_write_protected_by_lock(self):
        """Concurrent cache hits must not corrupt _cached_markers.

        Submits 8 IOCs concurrently to an adapter with a mock cache that always
        returns hits. After completion, cached_markers must contain exactly 8 entries
        (no missing entries, no KeyError).
        """
        iocs = [_make_ioc(IOCType.IPV4, f"10.0.0.{i}") for i in range(8)]

        adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})

        # Build cache mock that returns hits for all IOCs
        cache_mock = MagicMock()
        cache_mock.get.side_effect = lambda value, type_, provider, ttl: {
            "provider": "VirusTotal",
            "verdict": "clean",
            "detection_count": 0,
            "total_engines": 10,
            "cached_at": "2024-01-01T00:00:00",
        }

        orchestrator = EnrichmentOrchestrator(
            adapters=[adapter],
            max_workers=8,
            cache=cache_mock,
        )

        orchestrator.enrich_all("job-marker-lock", iocs)

        markers = orchestrator.cached_markers
        # All 8 IOCs should have a marker entry (no missing, no corruption)
        assert len(markers) == 8, (
            f"Expected 8 cached_markers entries, got {len(markers)}. "
            "Concurrent writes without _lock can cause lost updates."
        )
        for ioc in iocs:
            key = f"{ioc.value}|VirusTotal"
            assert key in markers, f"Missing cached_markers entry for {key}"
