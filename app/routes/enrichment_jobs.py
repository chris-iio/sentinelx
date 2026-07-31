"""Enrichment job lifecycle, polling status, and save diagnostics."""

import logging
import uuid
from collections.abc import Callable
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore, Lock

from flask import current_app, jsonify, request

from app.enrichment.config_store import ConfigStore
from app.enrichment.history_diagnostics import record_history_save_outcome
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.models import IOC
from app.text_utils import stripped_text_or_none

from . import enrichment_status
from .enrichment_diagnostics import build_orchestration_diagnostics_snapshot
from .enrichment_history import save_enrichment_status_history
from .enrichment_job_registry import registered_job_state, register_orchestrator_state
from .json_results import apply_json_result
from .query_values import status_cursor_from_query

logger = logging.getLogger(__name__)

__all__ = (
    "get_orchestration_diagnostics_snapshot",
)

# Module-level registry mapping job_id -> EnrichmentOrchestrator instance.
# SEC-18: Bounded OrderedDict with LRU eviction to prevent memory exhaustion.
# M012 S01: keep short terminal tombstones so pollers can tell eviction apart
# from a never-seen job id.
_MAX_ORCHESTRATORS = 200
_orchestrators: OrderedDict[str, EnrichmentOrchestrator] = OrderedDict()
_terminal_jobs: OrderedDict[str, dict] = OrderedDict()
_orch_lock = Lock()

# Keep four active jobs and at most four queued jobs.
_MAX_OUTSTANDING_ENRICHMENTS = 8
_enrichment_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="enrich")
_enrichment_slots = BoundedSemaphore(_MAX_OUTSTANDING_ENRICHMENTS)


class EnrichmentCapacityError(RuntimeError):
    """Raised when the bounded enrichment executor has no available slot."""


def get_orchestration_diagnostics_snapshot(job_id: str) -> dict[str, object]:
    """Return a copied, secret-free orchestration diagnostics snapshot.

    This accessor is intentionally narrow for backend diagnostic exports: it
    never returns orchestrator instances, live result objects, or mutable job
    internals. Missing/evicted jobs are represented as safe snapshots so the
    diagnostic manifest can show that the optional job context was considered.
    """
    normalized_job_id = stripped_text_or_none(str(job_id or "")) or ""
    if not normalized_job_id:
        return {"job_id": "", "found": False, "reason": "job_id_not_provided"}

    job_state = registered_job_state(
        lock=_orch_lock,
        orchestrators=_orchestrators,
        terminal_jobs=_terminal_jobs,
        job_id=normalized_job_id,
    )
    return build_orchestration_diagnostics_snapshot(
        job_id=normalized_job_id,
        orchestrator=job_state.orchestrator,
        terminal_job=job_state.terminal,
    )


def _build_enrichment_orchestrator(
    *,
    registry: object,
    cache: object,
    configured_providers: list[object] | None = None,
    config_store_factory: Callable[[], object] = ConfigStore,
) -> EnrichmentOrchestrator:
    """Return an enrichment orchestrator from registry/cache runtime dependencies."""
    config_store = config_store_factory()
    cache_ttl_hours = config_store.get_cache_ttl()  # type: ignore[attr-defined]
    adapters = configured_providers if configured_providers is not None else registry.configured()  # type: ignore[attr-defined]
    return EnrichmentOrchestrator(
        adapters=adapters,
        cache=cache,
        cache_ttl_seconds=cache_ttl_hours * 3600,
    )


def _resolve_orchestrator_runtime_dependencies(
    *,
    registry: object | None = None,
    cache: object | None = None,
) -> tuple[object, object]:
    """Return explicit registry/cache dependencies, falling back to current app state."""
    return (
        current_app.registry if registry is None else registry,
        current_app.cache_store if cache is None else cache,
    )


def _register_orchestrator(job_id: str, orchestrator: EnrichmentOrchestrator) -> None:
    """Register a live orchestrator and retain bounded terminal eviction state."""
    with _orch_lock:
        register_orchestrator_state(
            orchestrators=_orchestrators,
            terminal_jobs=_terminal_jobs,
            job_id=job_id,
            orchestrator=orchestrator,
            max_jobs=_MAX_ORCHESTRATORS,
            evicted_status=enrichment_status.evicted_terminal_status,
        )


def _save_job_history(
    orchestrator: EnrichmentOrchestrator,
    job_id: str,
    iocs: list[IOC],
    input_text: str,
    mode: str,
    history_store: object,
) -> None:
    """Save terminal job evidence without changing its enrichment outcome."""
    try:
        save_enrichment_status_history(
            status=orchestrator.get_status(job_id),
            history_store=history_store,
            input_text=input_text,
            mode=mode,
            iocs=iocs,
            analysis_id=job_id,
        )
    except Exception as exc:
        record_history_save_outcome("failed", error=exc)
        logger.warning("Failed to save analysis %s to history", job_id, exc_info=True)


def _run_enrichment_and_save(
    orchestrator: EnrichmentOrchestrator,
    job_id: str,
    iocs: list[IOC],
    input_text: str,
    mode: str,
    history_store: object,
) -> None:
    """Run enrichment and save complete or failed evidence to history."""
    orchestrator.enrich_all(job_id, iocs)
    _save_job_history(orchestrator, job_id, iocs, input_text, mode, history_store)


def _run_enrichment_with_slot(
    orchestrator: EnrichmentOrchestrator,
    job_id: str,
    iocs: list[IOC],
    text: str,
    mode: str,
    history_store: object,
    slots: BoundedSemaphore,
) -> None:
    """Run one accepted job and always release its outstanding-work slot."""
    try:
        _run_enrichment_and_save(
            orchestrator,
            job_id,
            iocs,
            text,
            mode,
            history_store,
        )
    finally:
        slots.release()


def _submit_enrichment_job(
    *,
    orchestrator: EnrichmentOrchestrator,
    job_id: str,
    iocs: list[IOC],
    text: str,
    mode: str,
    history_store: object,
    executor: ThreadPoolExecutor | None = None,
    slots: BoundedSemaphore | None = None,
) -> bool:
    """Submit one job or mark its queued state with a clear overload failure."""
    pool = executor if executor is not None else _enrichment_pool

    # Non-ThreadPoolExecutor integrations own their submission capacity.
    if executor is None and not isinstance(pool, ThreadPoolExecutor):
        pool.submit(  # type: ignore[union-attr]
            _run_enrichment_and_save,
            orchestrator,
            job_id,
            iocs,
            text,
            mode,
            history_store,
        )
        return True

    capacity = slots if slots is not None else _enrichment_slots
    if not capacity.acquire(blocking=False):
        orchestrator.fail_job(
            job_id,
            EnrichmentCapacityError(
                "Enrichment capacity is full. Retry the analysis shortly."
            ),
            reason="overloaded",
        )
        _save_job_history(orchestrator, job_id, iocs, text, mode, history_store)
        return False

    try:
        pool.submit(
            _run_enrichment_with_slot,
            orchestrator,
            job_id,
            iocs,
            text,
            mode,
            history_store,
            capacity,
        )
    except Exception as exc:
        capacity.release()
        orchestrator.fail_job(job_id, exc, reason="submission_failed")
        _save_job_history(orchestrator, job_id, iocs, text, mode, history_store)
        return False
    return True


def _setup_orchestrator(
    iocs: list[IOC],
    text: str,
    mode: str,
    history_store: object,
    configured_providers: list[object] | None = None,
    *,
    registry: object | None = None,
    cache: object | None = None,
    config_store_factory: Callable[[], object] = ConfigStore,
) -> tuple[str, EnrichmentOrchestrator, object]:
    """Create an orchestrator, register it, and submit the enrichment job."""
    job_id = uuid.uuid4().hex
    resolved_registry, resolved_cache = _resolve_orchestrator_runtime_dependencies(
        registry=registry,
        cache=cache,
    )
    orchestrator = _build_enrichment_orchestrator(
        registry=resolved_registry,
        cache=resolved_cache,
        configured_providers=configured_providers,
        config_store_factory=config_store_factory,
    )

    orchestrator.register_queued_job(job_id, iocs)
    _register_orchestrator(job_id, orchestrator)

    _submit_enrichment_job(
        orchestrator=orchestrator,
        job_id=job_id,
        iocs=iocs,
        text=text,
        mode=mode,
        history_store=history_store,
    )

    return job_id, orchestrator, resolved_registry


def _get_enrichment_status(job_id: str):
    """Shared status endpoint body for both HTML and API routes."""
    since = status_cursor_from_query(request.args)

    job_state = registered_job_state(
        lock=_orch_lock,
        orchestrators=_orchestrators,
        terminal_jobs=_terminal_jobs,
        job_id=job_id,
    )

    result = enrichment_status.enrichment_status_response(
        job_id,
        orchestrator=job_state.orchestrator,
        terminal=job_state.terminal,
        since=since,
    )
    return apply_json_result(result, jsonify_response=jsonify)
