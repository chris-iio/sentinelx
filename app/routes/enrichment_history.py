"""History persistence helpers for terminal enrichment jobs."""

from __future__ import annotations

from app.enrichment.history_diagnostics import (
    record_history_save_attempt,
    record_history_save_outcome,
)
from app.pipeline.models import IOC
from . import enrichment_status
from .ioc_payloads import _serialize_iocs


def save_enrichment_history(
    *,
    history_store: object,
    input_text: str,
    mode: str,
    iocs: list[IOC],
    results: list[object],
    workflow: dict[str, object],
    analysis_id: str,
) -> None:
    """Serialize and persist provider evidence plus separate workflow metadata."""
    saved_results = enrichment_status.serialize_results(results)  # type: ignore[arg-type]
    saved_results.append(workflow)
    history_store.save_analysis(  # type: ignore[union-attr]
        input_text=input_text,
        mode=mode,
        iocs=_serialize_iocs(iocs),
        results=saved_results,
        analysis_id=analysis_id,
    )


def _workflow_history_record(status: dict[str, object]) -> dict[str, object]:
    """Return job state metadata that is not provider evidence."""
    workflow_status = status.get("status")
    if not isinstance(workflow_status, str):
        workflow_status = "complete" if status.get("complete") is True else "failed"
    return {
        "type": "workflow",
        "status": workflow_status,
        "complete": status.get("complete") is True,
        "terminal": status.get("terminal") is True,
        "terminal_reason": status.get("terminal_reason"),
        "error": status.get("error"),
        "done": status.get("done", 0),
        "total": status.get("total", 0),
    }


def save_enrichment_status_history(
    *,
    status: dict[str, object] | None,
    history_store: object,
    input_text: str,
    mode: str,
    iocs: list[IOC],
    analysis_id: str,
) -> str:
    """Persist a terminal status payload and record the save diagnostic outcome."""
    if mode != "online" or status is None or status.get("status") in {"queued", "running"}:
        record_history_save_outcome("skipped")
        return "skipped"

    raw_results = status.get("results")
    results = list(raw_results) if isinstance(raw_results, list) else []
    record_history_save_attempt()
    save_enrichment_history(
        history_store=history_store,
        input_text=input_text,
        mode=mode,
        iocs=iocs,
        results=results,
        workflow=_workflow_history_record(status),
        analysis_id=analysis_id,
    )
    record_history_save_outcome("saved")
    return "saved"
