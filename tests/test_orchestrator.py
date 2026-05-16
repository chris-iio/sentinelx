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

import inspect
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    _BACKOFF_BASE,
    _MAX_RATE_LIMIT_RETRIES,
    _cached_enrichment_result,
    _normalize_provider_name,
    _provider_diagnostics_bucket,
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


class _NoItemsDict(dict):
    def items(self):
        raise AssertionError("orchestrator diagnostics should scan mapping keys directly")


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

        mock_adapter.lookup.side_effect = _make_result

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
        """get_status(job_id) returns progress keys plus terminal-semantics metadata."""
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
        assert "status" in status
        assert "terminal" in status
        assert "terminal_reason" in status
        assert "error" in status

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
        """get_status on a never-seen job_id returns None."""
        orchestrator = _make_orchestrator(mock_adapter)
        assert orchestrator.get_status("nonexistent") is None

    def test_job_status_complete_semantics(self, mock_adapter):
        """Completed jobs expose non-terminal terminal-semantics metadata."""
        ioc = _make_ioc(IOCType.IPV4, "7.7.7.8")
        mock_adapter.lookup.return_value = _make_result(ioc)

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-status-semantics", [ioc])

        status = orchestrator.get_status("job-status-semantics")
        assert status["status"] == "complete"
        assert status["terminal"] is False
        assert status["terminal_reason"] is None
        assert status["error"] is None


class TestLRUEviction:

    def test_job_cleanup_lru(self, mock_adapter):
        """Evicted jobs return an explicit terminal tombstone instead of disappearing."""
        ioc = _make_ioc(IOCType.IPV4, "9.9.9.9")
        mock_adapter.lookup.return_value = _make_result(ioc)

        # Use a small max_jobs to avoid creating 101 real jobs
        # We pass max_jobs=5, create 6 jobs, and verify first is evicted
        orchestrator = EnrichmentOrchestrator(adapters=[mock_adapter], max_workers=1, max_jobs=5)

        first_job_id = "job-lru-0"
        for i in range(6):
            job_id = f"job-lru-{i}"
            orchestrator.enrich_all(job_id, [ioc])

        # First job must expose an eviction tombstone after 6 jobs with maxsize=5
        first_status = orchestrator.get_status(first_job_id)
        assert first_status is not None
        assert first_status["status"] == "failed"
        assert first_status["terminal"] is True
        assert first_status["terminal_reason"] == "evicted"
        assert first_status["error"] == "Enrichment job status was evicted from memory."
        # Most recent job must still be present as a normal completed job
        latest_status = orchestrator.get_status("job-lru-5")
        assert latest_status is not None
        assert latest_status["status"] == "complete"


class TestJobFailureSemantics:
    """Prove unexpected worker exceptions become explicit terminal failures."""

    def test_unexpected_lookup_exception_marks_job_failed(self, mock_adapter):
        """Unhandled adapter exceptions should mark the job as failed and terminal."""
        ioc = _make_ioc(IOCType.IPV4, "11.11.11.11")
        mock_adapter.lookup.side_effect = RuntimeError("adapter exploded")

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-hard-fail", [ioc])

        status = orchestrator.get_status("job-hard-fail")
        assert status is not None
        assert status["complete"] is True
        assert status["status"] == "failed"
        assert status["terminal"] is True
        assert status["terminal_reason"] == "job_failed"
        assert status["error"] == "adapter exploded"
        assert status["done"] == 0
        assert status["results"] == []


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

    def test_zero_dispatch_job_skips_thread_pool(self, monkeypatch):
        """Jobs with no matching adapter work should complete without executor setup."""
        import app.enrichment.orchestrator as orchestrator_module

        ioc = _make_ioc(IOCType.DOMAIN, "evil.com")
        adapter = _make_mock_adapter(supported_types={IOCType.MD5})

        def fail_thread_pool(*_args, **_kwargs):
            raise AssertionError("zero-dispatch jobs should not construct a thread pool")

        monkeypatch.setattr(orchestrator_module, "ThreadPoolExecutor", fail_thread_pool)

        orchestrator = EnrichmentOrchestrator(adapters=[adapter], max_workers=4)
        orchestrator.enrich_all("job-zero-dispatch", [ioc])

        status = orchestrator.get_status("job-zero-dispatch")

        assert status is not None
        assert status["total"] == 0
        assert status["done"] == 0
        assert status["results"] == []
        assert status["complete"] is True
        assert status["status"] == "complete"
        assert adapter.lookup.call_count == 0

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

        VT has a brief gate (near-instant Event.wait). DNS is instant.
        All 16 results (8 VT + 8 DNS) must be present after enrich_all completes.
        """
        iocs = [_make_ioc(IOCType.IPV4, f"10.0.1.{i}") for i in range(8)]

        vt_adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})
        dns_adapter = _make_public_adapter("DNS", supported_types={IOCType.IPV4})

        vt_gate = threading.Event()  # never set — expires near-instantly

        def gated_vt_lookup(ioc):
            vt_gate.wait(timeout=0.01)  # near-instant expiry, no real delay
            return _make_result(ioc, provider="VirusTotal")

        vt_adapter.lookup.side_effect = gated_vt_lookup
        dns_adapter.lookup.side_effect = lambda ioc: _make_result(ioc, provider="DNS")

        orchestrator = EnrichmentOrchestrator(
            adapters=[vt_adapter, dns_adapter], max_workers=20
        )
        with patch("app.enrichment.orchestrator.time.sleep"):
            orchestrator.enrich_all("job-dns-free", iocs)

        status = orchestrator.get_status("job-dns-free")
        assert len(status["results"]) == 16, (
            f"Expected 16 results (8 VT + 8 DNS), got {len(status['results'])}"
        )
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
    return _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})


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

    def test_get_status_snapshot_copies_results_directly(self):
        """Full status snapshots should copy results with direct accumulation."""
        import inspect

        from app.enrichment.orchestrator import EnrichmentOrchestrator

        ioc = _make_ioc(IOCType.IPV4, "1.2.3.4")
        result = _make_result(ioc)
        orchestrator = _make_orchestrator(_make_mock_adapter())
        with orchestrator._lock:
            orchestrator._jobs["job-direct-copy"] = {
                "total": 1,
                "done": 1,
                "complete": True,
                "status": "complete",
                "terminal": False,
                "results": [result],
            }

        status = orchestrator.get_status("job-direct-copy")
        source = inspect.getsource(EnrichmentOrchestrator._status_snapshot)

        assert status["results"] == [result]
        assert status["results"] is not orchestrator._jobs["job-direct-copy"]["results"]
        assert "list(results)" not in source
        assert "_copy_results_tail(results, 0)" in source


class TestIncrementalStatusSnapshot:
    """Prove the additive tail snapshot path stays lock-safe and cursor-correct."""

    def test_get_incremental_status_nonnegative_since_does_not_slice_results(self, mock_adapter):
        """Non-negative cursors should avoid allocating an intermediate slice."""
        orchestrator = _make_orchestrator(mock_adapter)
        ioc_a = _make_ioc(IOCType.IPV4, "198.51.100.10")
        ioc_b = _make_ioc(IOCType.IPV4, "198.51.100.11")

        class NoSliceResults(list):
            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("incremental status should use bounded iteration")
                return super().__getitem__(index)

        results = NoSliceResults([
            _make_result(ioc_a, provider="ProviderA"),
            _make_result(ioc_b, provider="ProviderB"),
        ])

        with orchestrator._lock:
            orchestrator._jobs["job-no-slice-tail"] = {
                "total": 2,
                "done": 2,
                "results": results,
                "complete": True,
                "status": "complete",
                "terminal": False,
                "terminal_reason": None,
                "error": None,
                "_diagnostics": {},
            }

        snapshot = orchestrator.get_incremental_status("job-no-slice-tail", since=1)

        assert snapshot is not None
        assert snapshot["results"] == [results[1]]
        assert snapshot["next_since"] == 2
        assert snapshot["cached_markers"] == {}

    def test_get_incremental_status_copies_tail_without_list_constructor(self, mock_adapter):
        """Incremental tails should be accumulated directly from bounded iteration."""
        import inspect
        import app.enrichment.orchestrator as orchestrator_module

        source = inspect.getsource(orchestrator_module.EnrichmentOrchestrator._incremental_status_snapshot)

        assert "list(islice(" not in source
        assert "self._copy_results_tail(results, since)" in source
        assert "self._copy_results_tail(results, start)" in source

    def test_copy_results_tail_skips_iteration_for_short_tails(self, mock_adapter):
        """Tail copying should avoid iterator setup when the requested tail has two or fewer results."""
        orchestrator = _make_orchestrator(mock_adapter)
        first = _make_result(_make_ioc(IOCType.IPV4, "198.51.100.50"))
        second = _make_result(_make_ioc(IOCType.IPV4, "198.51.100.51"))

        class NoIterResults(list):
            def __iter__(self):
                raise AssertionError("short tail copying should not iterate")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("tail copying should not slice results")
                return super().__getitem__(index)

        results = NoIterResults([first, second])

        assert orchestrator._copy_results_tail(results, 2) == []
        assert orchestrator._copy_results_tail(results, 1) == [second]
        assert orchestrator._copy_results_tail(results, 0) == [first, second]
        assert "len" in orchestrator._copy_results_tail.__code__.co_names

    def test_get_incremental_status_returns_tail_and_aligned_cached_markers(self, mock_adapter):
        """Tail reads should include only requested results and matching cache markers."""
        orchestrator = _make_orchestrator(mock_adapter)
        ioc_a = _make_ioc(IOCType.IPV4, "198.51.100.1")
        ioc_b = _make_ioc(IOCType.IPV4, "198.51.100.2")
        ioc_c = _make_ioc(IOCType.IPV4, "198.51.100.3")
        result_a = _make_result(ioc_a, provider="ProviderA")
        result_b = _make_result(ioc_b, provider="ProviderB")
        result_c = _make_result(ioc_c, provider="ProviderC")

        with orchestrator._lock:
            orchestrator._jobs["job-incremental-tail"] = {
                "total": 3,
                "done": 3,
                "results": [result_a, result_b, result_c],
                "complete": True,
                "status": "complete",
                "terminal": False,
                "terminal_reason": None,
                "error": None,
                "_diagnostics": {},
            }
            orchestrator._cached_markers[f"{ioc_a.value}|ProviderA"] = "2024-01-01T00:00:00Z"
            orchestrator._cached_markers[f"{ioc_b.value}|ProviderB"] = "2024-01-02T00:00:00Z"

        snapshot = orchestrator.get_incremental_status("job-incremental-tail", since=1)
        assert snapshot is not None
        assert snapshot["results"] == [result_b, result_c]
        assert snapshot["next_since"] == 3
        assert snapshot["cached_markers"] == {
            f"{ioc_b.value}|ProviderB": "2024-01-02T00:00:00Z"
        }

        snapshot["results"].append(_make_error(ioc_a, msg="dummy", provider="ProviderA"))
        snapshot["cached_markers"][f"{ioc_b.value}|ProviderB"] = "tampered"

        fresh_snapshot = orchestrator.get_incremental_status("job-incremental-tail", since=1)
        assert fresh_snapshot is not None
        assert fresh_snapshot["results"] == [result_b, result_c]
        assert fresh_snapshot["cached_markers"] == {
            f"{ioc_b.value}|ProviderB": "2024-01-02T00:00:00Z"
        }

        full_snapshot = orchestrator.get_status("job-incremental-tail")
        assert full_snapshot is not None
        assert full_snapshot["results"] == [result_a, result_b, result_c]

    def test_get_incremental_status_builds_scalar_fields_without_items_scan(self, mock_adapter):
        """Polling snapshots should copy known scalar fields directly."""
        orchestrator = _make_orchestrator(mock_adapter)
        ioc = _make_ioc(IOCType.IPV4, "198.51.100.44")
        result = _make_result(ioc, provider="ProviderA")

        class NoItemsJob(dict):
            def items(self):
                raise AssertionError("status snapshots should not scan every job item")

        with orchestrator._lock:
            orchestrator._jobs["job-no-items-snapshot"] = NoItemsJob({
                "total": 1,
                "done": 1,
                "results": [result],
                "complete": True,
                "status": "complete",
                "terminal": False,
                "terminal_reason": None,
                "error": None,
                "_diagnostics": {"ignored": True},
            })

        snapshot = orchestrator.get_incremental_status("job-no-items-snapshot", since=0)

        assert snapshot is not None
        assert snapshot["total"] == 1
        assert snapshot["done"] == 1
        assert snapshot["status"] == "complete"
        assert snapshot["results"] == [result]
        assert "_diagnostics" not in snapshot

    def test_get_incremental_status_preserves_negative_since_behavior(self, mock_adapter):
        """Negative since values should keep slice semantics without slicing results."""
        orchestrator = _make_orchestrator(mock_adapter)
        iocs = [_make_ioc(IOCType.IPV4, f"203.0.113.{i}") for i in range(3)]

        class NoSliceResults(list):
            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("negative incremental cursors should use bounded iteration")
                return super().__getitem__(index)

        results = NoSliceResults(
            [_make_result(ioc, provider=f"Provider{i}") for i, ioc in enumerate(iocs)]
        )

        with orchestrator._lock:
            orchestrator._jobs["job-negative-since"] = {
                "total": 3,
                "done": 3,
                "results": results,
                "complete": True,
                "status": "complete",
                "terminal": False,
                "terminal_reason": None,
                "error": None,
                "_diagnostics": {},
            }

        snapshot = orchestrator.get_incremental_status("job-negative-since", since=-1)
        assert snapshot is not None
        assert snapshot["results"] == [results[-1]]
        assert snapshot["next_since"] == 3
        assert snapshot["cached_markers"] == {}

    def test_get_incremental_status_returns_empty_tail_beyond_retained_length(self, mock_adapter):
        """Out-of-range since values should return an empty tail without walking results."""
        orchestrator = _make_orchestrator(mock_adapter)
        ioc_a = _make_ioc(IOCType.IPV4, "192.0.2.40")
        ioc_b = _make_ioc(IOCType.IPV4, "192.0.2.41")

        class NoWalkResults(list):
            def __iter__(self):
                raise AssertionError("empty out-of-range tails should not iterate results")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("empty out-of-range tails should not slice results")
                return super().__getitem__(index)

        with orchestrator._lock:
            orchestrator._jobs["job-since-beyond"] = {
                "total": 2,
                "done": 2,
                "results": NoWalkResults([_make_result(ioc_a), _make_result(ioc_b)]),
                "complete": True,
                "status": "complete",
                "terminal": False,
                "terminal_reason": None,
                "error": None,
                "_diagnostics": {},
            }

        snapshot = orchestrator.get_incremental_status("job-since-beyond", since=99)
        assert snapshot is not None
        assert snapshot["results"] == []
        assert snapshot["next_since"] == 2
        assert snapshot["cached_markers"] == {}

    def test_get_incremental_status_preserves_terminal_failed_cursor_defaults(self, mock_adapter):
        """Failed terminal jobs should expose empty tails plus the safe cursor fallback."""
        ioc = _make_ioc(IOCType.IPV4, "11.11.11.11")
        mock_adapter.lookup.side_effect = RuntimeError("adapter exploded")

        orchestrator = _make_orchestrator(mock_adapter)
        orchestrator.enrich_all("job-hard-fail-incremental", [ioc])

        snapshot = orchestrator.get_incremental_status("job-hard-fail-incremental", since=4)
        assert snapshot is not None
        assert snapshot["status"] == "failed"
        assert snapshot["terminal"] is True
        assert snapshot["terminal_reason"] == "job_failed"
        assert snapshot["error"] == "adapter exploded"
        assert snapshot["results"] == []
        assert snapshot["next_since"] == 4
        assert snapshot["cached_markers"] == {}

    def test_get_incremental_status_returns_eviction_tombstone_and_none_for_unknown_job(self):
        """Evicted jobs should keep tombstones; unknown jobs should still return None."""
        ioc = _make_ioc(IOCType.IPV4, "9.9.9.9")
        adapter = _make_public_adapter("VirusTotal", supported_types={IOCType.IPV4})
        adapter.lookup.return_value = _make_result(ioc, provider="VirusTotal")

        orchestrator = EnrichmentOrchestrator(adapters=[adapter], max_workers=1, max_jobs=1)
        orchestrator.enrich_all("job-evicted-0", [ioc])
        orchestrator.enrich_all("job-evicted-1", [ioc])

        evicted = orchestrator.get_incremental_status("job-evicted-0", since=7)
        assert evicted is not None
        assert evicted["status"] == "failed"
        assert evicted["terminal"] is True
        assert evicted["terminal_reason"] == "evicted"
        assert evicted["results"] == []
        assert evicted["next_since"] == 7
        assert evicted["cached_markers"] == {}

        assert orchestrator.get_incremental_status("job-unknown") is None


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

    def test_cached_markers_snapshot_copies_directly(self, mock_adapter):
        """cached_markers should return an isolated snapshot without dict() copying."""
        import inspect

        orchestrator = _make_orchestrator(mock_adapter)
        with orchestrator._lock:
            orchestrator._cached_markers["1.2.3.4|VirusTotal"] = "2026-05-01T00:00:00Z"

        markers = orchestrator.cached_markers
        markers["1.2.3.4|VirusTotal"] = "tampered"

        source = inspect.getsource(EnrichmentOrchestrator.cached_markers.fget)
        assert "dict(self._cached_markers)" not in source
        assert orchestrator.cached_markers == {
            "1.2.3.4|VirusTotal": "2026-05-01T00:00:00Z"
        }

    def test_cache_hit_hydration_preserves_cached_payload(self):
        """Cache hits should not remove cached_at from the cache payload dict."""
        ioc = _make_ioc(IOCType.IPV4, "10.0.0.9")
        adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})
        cached_payload = {
            "provider": "VirusTotal",
            "verdict": "clean",
            "detection_count": 0,
            "total_engines": 10,
            "scan_date": None,
            "raw_stats": {},
            "cached_at": "2024-01-01T00:00:00",
        }
        cache_mock = MagicMock()
        cache_mock.get.return_value = cached_payload

        orchestrator = EnrichmentOrchestrator(
            adapters=[adapter],
            max_workers=1,
            cache=cache_mock,
        )
        orchestrator.enrich_all("job-cache-payload", [ioc])

        status = orchestrator.get_status("job-cache-payload")
        assert isinstance(status["results"][0], EnrichmentResult)
        assert cached_payload["cached_at"] == "2024-01-01T00:00:00"
        assert "pop" not in inspect.getsource(_cached_enrichment_result)


class TestJobDiagnostics:
    """Prove orchestrator-owned runtime/provider diagnostics stay bounded and safe."""

    def test_dispatch_diagnostics_reuses_provider_bucket_without_setdefault(self):
        """Initial dispatch diagnostics should avoid eager default bucket allocation."""
        ioc_a = _make_ioc(IOCType.IPV4, "198.51.100.10")
        ioc_b = _make_ioc(IOCType.IPV4, "198.51.100.11")
        adapter = _make_public_adapter("VirusTotal", supported_types={IOCType.IPV4})
        orchestrator = _make_orchestrator(adapter)

        diagnostics = orchestrator._build_dispatch_diagnostics([
            (adapter, ioc_a),
            (adapter, ioc_b),
        ])

        assert diagnostics["dispatch_count"] == 2
        assert diagnostics["providers"]["VirusTotal"]["dispatch_count"] == 2
        assert "setdefault" not in EnrichmentOrchestrator._build_dispatch_diagnostics.__code__.co_names
        assert "setdefault" not in _provider_diagnostics_bucket.__code__.co_names

    def test_diagnostics_track_cache_hits_misses_and_unknown_provider_bucket(self):
        """Blank adapter names should fall into a bounded unknown bucket."""
        ioc_hit = _make_ioc(IOCType.IPV4, "198.51.100.10")
        ioc_miss = _make_ioc(IOCType.IPV4, "198.51.100.11")

        adapter = _make_keyed_adapter("   ", supported_types={IOCType.IPV4})
        adapter.lookup.side_effect = lambda ioc: _make_result(ioc, provider="FallbackProvider")

        cache_mock = MagicMock()
        cache_mock.get.side_effect = lambda value, type_, provider, ttl: (
            {
                "provider": "FallbackProvider",
                "verdict": "clean",
                "detection_count": 0,
                "total_engines": 10,
                "cached_at": "2024-01-01T00:00:00",
            }
            if value == ioc_hit.value and provider == "unknown"
            else None
        )

        orchestrator = EnrichmentOrchestrator(
            adapters=[adapter],
            max_workers=2,
            cache=cache_mock,
            provider_concurrency={"unknown": 1},
        )
        orchestrator.enrich_all("job-diagnostics-cache", [ioc_hit, ioc_miss])

        diagnostics = orchestrator.get_diagnostics("job-diagnostics-cache")
        assert diagnostics is not None
        assert diagnostics["dispatch_count"] == 2
        assert diagnostics["attempt_count"] == 2
        assert diagnostics["cache_hits"] == 1
        assert diagnostics["cache_misses"] == 1
        assert diagnostics["retry_count"] == 0
        assert diagnostics["rate_limit_retry_count"] == 0
        assert diagnostics["error_count"] == 0
        assert "unknown" in diagnostics["providers"]
        assert "unknown" in orchestrator._semaphores

        unknown_provider = diagnostics["providers"]["unknown"]
        assert unknown_provider["dispatch_count"] == 2
        assert unknown_provider["attempt_count"] == 2
        assert unknown_provider["cache_hits"] == 1
        assert unknown_provider["cache_misses"] == 1
        assert unknown_provider["error_count"] == 0

    def test_provider_name_normalization_uses_index_trim_without_strip(self):
        class NoStripProviderName(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("provider normalization should avoid direct strip allocation")

        assert _normalize_provider_name(NoStripProviderName("  VirusTotal  ")) == "VirusTotal"
        assert _normalize_provider_name(NoStripProviderName(" \n\t ")) == "unknown"
        assert "strip" not in _normalize_provider_name.__code__.co_names

    def test_diagnostics_track_rate_limit_retry_error_and_latency_aggregates(self):
        """429 retries should increment retry counters without changing retry flow."""
        ioc = _make_ioc(IOCType.IPV4, "203.0.113.10")
        adapter = _make_vt_adapter()
        adapter.lookup.side_effect = [
            _make_error(ioc, msg="HTTP 429", provider="VirusTotal"),
            _make_result(ioc, provider="VirusTotal"),
        ]

        orchestrator = _make_orchestrator(adapter)
        with patch(
            "app.enrichment.orchestrator.time.perf_counter",
            side_effect=[10.0, 10.5, 20.0, 21.25],
        ), patch("app.enrichment.orchestrator.time.sleep"):
            orchestrator.enrich_all("job-diagnostics-429", [ioc])

        diagnostics = orchestrator.get_diagnostics("job-diagnostics-429")
        assert diagnostics is not None
        assert diagnostics["dispatch_count"] == 1
        assert diagnostics["attempt_count"] == 2
        assert diagnostics["retry_count"] == 1
        assert diagnostics["rate_limit_retry_count"] == 1
        assert diagnostics["error_count"] == 1
        assert diagnostics["latency_total_seconds"] == pytest.approx(1.75)
        assert diagnostics["latency_max_seconds"] == pytest.approx(1.25)

        vt_provider = diagnostics["providers"]["VirusTotal"]
        assert vt_provider["dispatch_count"] == 1
        assert vt_provider["attempt_count"] == 2
        assert vt_provider["retry_count"] == 1
        assert vt_provider["rate_limit_retry_count"] == 1
        assert vt_provider["error_count"] == 1
        assert vt_provider["latency_total_seconds"] == pytest.approx(1.75)
        assert vt_provider["latency_max_seconds"] == pytest.approx(1.25)

    def test_get_diagnostics_returns_stable_snapshot_while_workers_update(self):
        """Mutating a returned diagnostics snapshot must not affect the live job state."""
        iocs = [
            _make_ioc(IOCType.IPV4, "192.0.2.20"),
            _make_ioc(IOCType.IPV4, "192.0.2.21"),
        ]
        adapter = _make_public_adapter("VirusTotal", supported_types={IOCType.IPV4})

        started = 0
        started_lock = threading.Lock()
        all_started = threading.Event()
        release_lookup = threading.Event()

        def blocking_lookup(ioc):
            nonlocal started
            with started_lock:
                started += 1
                if started == len(iocs):
                    all_started.set()
            release_lookup.wait(timeout=2)
            return _make_result(ioc, provider="VirusTotal")

        adapter.lookup.side_effect = blocking_lookup
        orchestrator = _make_orchestrator(adapter, max_workers=2)

        worker = threading.Thread(
            target=orchestrator.enrich_all,
            args=("job-live-diagnostics", iocs),
        )
        worker.start()
        assert all_started.wait(timeout=2), "Workers did not start in time"

        live_snapshot = orchestrator.get_diagnostics("job-live-diagnostics")
        assert live_snapshot is not None
        assert live_snapshot["dispatch_count"] == 2
        assert live_snapshot["attempt_count"] == 0

        live_snapshot["dispatch_count"] = 999
        live_snapshot["providers"]["VirusTotal"]["dispatch_count"] = 999

        release_lookup.set()
        worker.join(timeout=2)
        assert not worker.is_alive(), "enrich_all thread did not finish"

        final_snapshot = orchestrator.get_diagnostics("job-live-diagnostics")
        assert final_snapshot is not None
        assert final_snapshot["dispatch_count"] == 2
        assert final_snapshot["attempt_count"] == 2
        assert final_snapshot["providers"]["VirusTotal"]["dispatch_count"] == 2
        assert final_snapshot["providers"]["VirusTotal"]["attempt_count"] == 2

    def test_get_diagnostics_falls_back_to_safe_defaults_for_malformed_state(self, mock_adapter):
        """Malformed internal diagnostics should coerce to bounded safe defaults."""
        orchestrator = _make_orchestrator(mock_adapter)
        with orchestrator._lock:
            orchestrator._jobs["job-malformed-diagnostics"] = {
                "_diagnostics": {
                    "dispatch_count": "oops",
                    "cache_hits": -1,
                    "providers": _NoItemsDict({
                        "   ": {"cache_hits": 2, "latency_max_seconds": 0.75},
                        "VirusTotal": "broken",
                    }),
                }
            }

        diagnostics = orchestrator.get_diagnostics("job-malformed-diagnostics")
        assert diagnostics == {
            "dispatch_count": 0,
            "attempt_count": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "retry_count": 0,
            "rate_limit_retry_count": 0,
            "error_count": 0,
            "latency_total_seconds": 0.0,
            "latency_max_seconds": 0.0,
            "providers": {
                "unknown": {
                    "dispatch_count": 0,
                    "attempt_count": 0,
                    "cache_hits": 2,
                    "cache_misses": 0,
                    "retry_count": 0,
                    "rate_limit_retry_count": 0,
                    "error_count": 0,
                    "latency_total_seconds": 0.0,
                    "latency_max_seconds": 0.75,
                },
                "VirusTotal": {
                    "dispatch_count": 0,
                    "attempt_count": 0,
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "retry_count": 0,
                    "rate_limit_retry_count": 0,
                    "error_count": 0,
                    "latency_total_seconds": 0.0,
                    "latency_max_seconds": 0.0,
                },
            },
        }
