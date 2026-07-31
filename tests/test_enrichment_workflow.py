"""Focused behavior tests for enrichment queueing, bounds, and failure isolation."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.enrichment import job_execution
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.models import IOC, IOCType
from app.routes import enrichment_status
from app.routes import enrichment_jobs
from app.routes.enrichment_jobs import _submit_enrichment_job


def _ioc(value: str = "203.0.113.10") -> IOC:
    return IOC(type=IOCType.IPV4, value=value, raw_match=value)


def _result(ioc: IOC, provider: str) -> EnrichmentResult:
    return EnrichmentResult(
        ioc=ioc,
        provider=provider,
        verdict="clean",
        detection_count=0,
        total_engines=1,
        scan_date=None,
        raw_stats={},
    )


def _adapter(name: str, lookup) -> MagicMock:
    adapter = MagicMock()
    adapter.name = name
    adapter.requires_api_key = False
    adapter.supported_types = {IOCType.IPV4}
    adapter.lookup.side_effect = lookup
    return adapter


def test_queued_job_poll_is_known_before_execution() -> None:
    ioc = _ioc()
    adapter = _adapter("ProviderA", lambda seen: _result(seen, "ProviderA"))
    orchestrator = EnrichmentOrchestrator([adapter])
    orchestrator.register_queued_job("queued-job", [ioc])

    response = enrichment_status.enrichment_status_response(
        "queued-job",
        orchestrator=orchestrator,
        terminal=None,
        since=0,
    )

    assert response.status == 200
    assert response.payload["status"] == "queued"
    assert response.payload["complete"] is False
    assert response.payload["terminal"] is False


def test_setup_registers_queued_state_before_executor_submission(monkeypatch) -> None:
    events: list[str] = []
    orchestrator = MagicMock()
    orchestrator.register_queued_job.side_effect = lambda *_args: events.append("queued")

    monkeypatch.setattr(
        enrichment_jobs,
        "_build_enrichment_orchestrator",
        lambda **_kwargs: orchestrator,
    )
    monkeypatch.setattr(
        enrichment_jobs,
        "_register_orchestrator",
        lambda *_args: events.append("route-registered"),
    )
    monkeypatch.setattr(
        enrichment_jobs,
        "_submit_enrichment_job",
        lambda **_kwargs: events.append("submitted"),
    )
    monkeypatch.setattr(
        enrichment_jobs.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex="ordered-job"),
    )

    job_id, _, _ = enrichment_jobs._setup_orchestrator(
        [_ioc()],
        "203.0.113.10",
        "online",
        object(),
        [],
        registry=object(),
        cache=object(),
        config_store_factory=object,
    )

    assert job_id == "ordered-job"
    assert events == ["queued", "route-registered", "submitted"]


def test_full_executor_capacity_marks_registered_job_overloaded() -> None:
    slots = BoundedSemaphore(1)
    assert slots.acquire(blocking=False)
    executor = ThreadPoolExecutor(max_workers=1)
    orchestrator = MagicMock()
    orchestrator.get_status.return_value = {
        "status": "failed",
        "terminal_reason": "overloaded",
        "error": "Enrichment capacity is full. Retry the analysis shortly.",
        "results": [],
    }
    history_store = MagicMock()

    try:
        accepted = _submit_enrichment_job(
            orchestrator=orchestrator,
            job_id="overloaded-job",
            iocs=[_ioc()],
            text="203.0.113.10",
            mode="online",
            history_store=history_store,
            executor=executor,
            slots=slots,
        )
    finally:
        slots.release()
        executor.shutdown(wait=True)

    assert accepted is False
    orchestrator.fail_job.assert_called_once()
    assert orchestrator.fail_job.call_args.kwargs["reason"] == "overloaded"
    assert "capacity is full" in str(orchestrator.fail_job.call_args.args[1])
    assert history_store.save_analysis.call_count == 1


def test_cache_exception_is_one_provider_outcome_and_preserves_other_evidence() -> None:
    ioc = _ioc()
    bad = _adapter("BadCache", lambda seen: _result(seen, "BadCache"))
    good = _adapter("GoodProvider", lambda seen: _result(seen, "GoodProvider"))
    cache = MagicMock()

    def cache_get(_value, _ioc_type, provider, _ttl):
        if provider == "BadCache":
            raise RuntimeError("cache unavailable")
        return None

    cache.get.side_effect = cache_get
    orchestrator = EnrichmentOrchestrator([bad, good], cache=cache, max_workers=2)

    with patch("app.enrichment.orchestrator.time.sleep"):
        orchestrator.enrich_all("partial-cache", [ioc])

    status = orchestrator.get_status("partial-cache")
    assert status is not None
    assert status["done"] == status["total"] == 2
    assert status["complete"] is False
    assert status["status"] == "failed"
    assert status["terminal_reason"] == "partial_failure"
    assert any(isinstance(item, EnrichmentResult) for item in status["results"])
    errors = [item for item in status["results"] if isinstance(item, EnrichmentError)]
    assert len(errors) == 1
    assert errors[0].provider == "BadCache"
    assert errors[0].error == "cache read failed: cache unavailable"


def test_unexpected_future_exception_is_recorded_without_stopping_other_futures() -> None:
    good_ioc = _ioc("203.0.113.11")
    bad_ioc = _ioc("203.0.113.12")
    adapter = _adapter("ProviderA", lambda _seen: None)
    recorded: list[EnrichmentResult | EnrichmentError] = []

    def lookup(_job_id, _adapter, seen_ioc):
        if seen_ioc == bad_ioc:
            raise RuntimeError("worker exploded")
        return _result(seen_ioc, "ProviderA")

    job_execution.run_dispatch_pairs(
        "future-job",
        [(adapter, bad_ioc), (adapter, good_ioc)],
        max_workers=2,
        lookup=lookup,
        record_result=lambda _job_id, result: recorded.append(result),
    )

    assert len(recorded) == 2
    assert any(isinstance(item, EnrichmentResult) for item in recorded)
    errors = [item for item in recorded if isinstance(item, EnrichmentError)]
    assert len(errors) == 1
    assert errors[0].provider == "ProviderA"
    assert errors[0].error == "provider worker failed: worker exploded"
