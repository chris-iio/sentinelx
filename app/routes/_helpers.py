"""Shared state and utilities for route modules.

Module-level state lives here so that analysis (which creates orchestrators)
and enrichment_status (which reads them) share the same registry.
"""

import logging
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from flask import current_app, jsonify, request

from app.enrichment.config_store import ConfigStore
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.models import IOC

logger = logging.getLogger(__name__)

# Module-level registry mapping job_id -> EnrichmentOrchestrator instance.
# SEC-18: Bounded OrderedDict with LRU eviction to prevent memory exhaustion.
# M012 S01: keep short terminal tombstones so pollers can tell eviction apart
# from a never-seen job id.
_MAX_ORCHESTRATORS = 200
_orchestrators: OrderedDict[str, EnrichmentOrchestrator] = OrderedDict()
_terminal_jobs: OrderedDict[str, dict] = OrderedDict()
_orch_lock = Lock()

# Shared thread pool for enrichment jobs — caps concurrent enrichments to 4.
_enrichment_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="enrich")


def _mask_key(key: str | None) -> str | None:
    """Return key with all but the last 4 characters replaced by asterisks.

    Returns None if key is None or shorter than 4 characters.
    """
    if not key or len(key) <= 4:
        return None
    return "*" * (len(key) - 4) + key[-4:]


def _serialize_result(
    r: EnrichmentResult | EnrichmentError,
    cached_markers: dict[str, str] | None = None,
) -> dict:
    """Serialize an enrichment result or error to a JSON-safe dict."""
    if isinstance(r, EnrichmentResult):
        d: dict = {
            "type": "result",
            "ioc_value": r.ioc.value,
            "ioc_type": r.ioc.type.value,
            "provider": r.provider,
            "verdict": r.verdict,
            "detection_count": r.detection_count,
            "total_engines": r.total_engines,
            "scan_date": r.scan_date,
            "raw_stats": r.raw_stats,
        }
        if cached_markers is not None:
            cache_key = r.ioc.value + "|" + r.provider
            cached_at = cached_markers.get(cache_key)
            if cached_at:
                d["cached_at"] = cached_at
        return d
    return {
        "type": "error",
        "ioc_value": r.ioc.value,
        "ioc_type": r.ioc.type.value,
        "provider": r.provider,
        "error": r.error,
    }


def _build_status_payload(status: dict, serialized_results: list[dict]) -> dict:
    """Normalize status responses for both live progress and terminal states.

    Contract:
    - status="running": in-flight job; complete=false, terminal=false.
    - status="complete": successful terminal state; complete=true, terminal=false.
    - status="failed": terminal failure; complete=true, terminal=true and
      terminal_reason identifies why (e.g. unknown, evicted, job_failed).

    Existing progress fields stay intact so cursor polling semantics do not change.
    """
    return {
        "total": status["total"],
        "done": status["done"],
        "complete": status["complete"],
        "results": serialized_results,
        "next_since": status.get("next_since", len(status.get("results", []))),
        "status": status.get("status", "complete" if status["complete"] else "running"),
        "terminal": status.get("terminal", False),
        "terminal_reason": status.get("terminal_reason"),
        "error": status.get("error"),
    }


def _terminal_status(job_id: str, *, reason: str, error: str, since: int = 0) -> dict:
    """Return a terminal status payload for missing/evicted/failed jobs."""
    return {
        "job_id": job_id,
        "total": 0,
        "done": 0,
        "complete": True,
        "results": [],
        "next_since": since,
        "status": "failed",
        "terminal": True,
        "terminal_reason": reason,
        "error": error,
    }


def _serialize_ioc(ioc: IOC) -> dict:
    """Serialize an IOC to a JSON-safe dict for history storage."""
    return {
        "type": ioc.type.value,
        "value": ioc.value,
        "raw_match": ioc.raw_match,
    }


def _run_enrichment_and_save(
    orchestrator: EnrichmentOrchestrator,
    job_id: str,
    iocs: list[IOC],
    input_text: str,
    mode: str,
    history_store: object,
) -> None:
    """Run enrichment and save results to history.

    Failures during history save are logged but do not break enrichment.
    """
    orchestrator.enrich_all(job_id, iocs)

    try:
        status = orchestrator.get_status(job_id)
        if status is None:
            return
        serialized_results = [_serialize_result(r) for r in status["results"]]
        serialized_iocs = [_serialize_ioc(ioc) for ioc in iocs]
        history_store.save_analysis(  # type: ignore[union-attr]
            input_text=input_text,
            mode=mode,
            iocs=serialized_iocs,
            results=serialized_results,
            analysis_id=job_id,
        )
    except Exception:
        logger.warning("Failed to save analysis %s to history", job_id, exc_info=True)


def _setup_orchestrator(
    iocs: list[IOC],
    text: str,
    mode: str,
    history_store: object,
) -> tuple[str, EnrichmentOrchestrator, object]:
    """Create an orchestrator, register it, and submit the enrichment job.

    Returns (job_id, orchestrator, registry). The 'not configured' guard
    stays in each caller since the response format differs (redirect vs JSON).
    """
    registry = current_app.registry
    job_id = uuid.uuid4().hex
    cache = current_app.cache_store
    config_store = ConfigStore()
    cache_ttl_hours = config_store.get_cache_ttl()
    orchestrator = EnrichmentOrchestrator(
        adapters=registry.configured(),
        cache=cache,
        cache_ttl_seconds=cache_ttl_hours * 3600,
    )

    with _orch_lock:
        _orchestrators[job_id] = orchestrator
        _terminal_jobs.pop(job_id, None)
        while len(_orchestrators) > _MAX_ORCHESTRATORS:
            evicted_job_id, _ = _orchestrators.popitem(last=False)
            _terminal_jobs[evicted_job_id] = _terminal_status(
                evicted_job_id,
                reason="evicted",
                error="Enrichment job status was evicted from memory.",
            )
        while len(_terminal_jobs) > _MAX_ORCHESTRATORS:
            _terminal_jobs.popitem(last=False)

    _enrichment_pool.submit(
        _run_enrichment_and_save,
        orchestrator, job_id, iocs, text, mode,
        history_store,
    )

    return job_id, orchestrator, registry


def _get_enrichment_status(job_id: str):
    """Shared status endpoint body for both HTML and API routes.

    Returns a Flask JSON response tuple. Success responses preserve the existing
    progress/cursor contract and add machine-readable terminal metadata. Missing
    responses stay 404 but now expose whether the poller hit an unknown id,
    helper-level eviction, orchestrator-level eviction, or a failed job.
    """
    since = request.args.get("since", 0, type=int)

    with _orch_lock:
        orchestrator = _orchestrators.get(job_id)
        terminal = _terminal_jobs.get(job_id)

    if orchestrator is None:
        payload = terminal or _terminal_status(
            job_id,
            reason="unknown",
            error="Enrichment job was not found.",
            since=since,
        )
        payload["next_since"] = since
        return jsonify(payload), 404

    status = orchestrator.get_status(job_id)
    if status is None:
        payload = _terminal_status(
            job_id,
            reason="unknown",
            error="Enrichment job was not found.",
            since=since,
        )
        return jsonify(payload), 404

    cached_markers = orchestrator.cached_markers
    all_results = status["results"]
    new_results = all_results[since:]
    serialized = [
        _serialize_result(r, cached_markers) for r in new_results
    ]

    status_payload = dict(status)
    status_payload["next_since"] = since if status_payload.get("terminal") else len(all_results)
    payload = _build_status_payload(status_payload, serialized)
    status_code = 404 if payload["terminal"] and payload["terminal_reason"] in {"unknown", "evicted"} else 200
    return jsonify(payload), status_code
