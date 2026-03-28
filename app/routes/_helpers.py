"""Shared state and utilities for route modules.

Module-level state lives here so that analysis (which creates orchestrators)
and enrichment_status (which reads them) share the same registry.
"""

import logging
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.models import IOC

logger = logging.getLogger(__name__)

# Module-level registry mapping job_id -> EnrichmentOrchestrator instance.
# SEC-18: Bounded OrderedDict with LRU eviction to prevent memory exhaustion.
_MAX_ORCHESTRATORS = 200
_orchestrators: OrderedDict[str, EnrichmentOrchestrator] = OrderedDict()
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
