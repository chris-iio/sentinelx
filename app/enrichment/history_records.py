"""Pure history row, payload, and verdict helpers."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from app.json_utils import decode_json_array, encode_json_array

# Shared summary precedence: malicious > suspicious > known_good > clean > no_data > error.
_VERDICT_PRIORITY = MappingProxyType(
    {
        "error": 0,
        "no_data": 1,
        "clean": 2,
        "known_good": 3,
        "suspicious": 4,
        "malicious": 5,
    }
)
_MAX_VERDICT = "malicious"
_FALLBACK_VERDICT = "error"


@dataclass(frozen=True, slots=True)
class _AnalysisInsertRecord:
    row_id: str
    values: tuple[object, ...]


def _summary_from_row(row) -> dict:
    return {
        "id": row[0],
        "input_text": row[1],
        "mode": row[2],
        "total_count": row[3],
        "top_verdict": row[4],
        "created_at": row[5],
    }


def _analysis_from_row(row) -> dict:
    iocs = _decode_json_array(row[3])
    results, workflow = _split_saved_results(_decode_json_array(row[4]))
    return {
        "id": row[0],
        "input_text": row[1],
        "mode": row[2],
        "iocs": iocs,
        "results": results,
        "workflow": workflow,
        "total_count": row[5],
        "top_verdict": row[6],
        "created_at": row[7],
    }


def _split_saved_results(payload: list[dict]) -> tuple[list[dict], dict | None]:
    """Separate provider evidence from the saved workflow metadata record."""
    results: list[dict] = []
    workflow = None
    for item in payload:
        if item.get("type") == "workflow":
            workflow = item
        else:
            results.append(item)
    return results, workflow


def _encode_json_array(payload: list[dict]) -> str:
    """Serialize a history payload, skipping JSON encoder work for empty lists."""
    return encode_json_array(payload)


def _decode_json_array(payload_json: str) -> list[dict]:
    """Deserialize a history payload, skipping JSON decoder work for empty lists."""
    return decode_json_array(payload_json)


def _coerce_max_rows(max_rows: int) -> int:
    """Return a positive retention row count."""
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows <= 0:
        raise ValueError("history max_rows must be a positive integer")
    return max_rows


def _analysis_insert_record(
    *,
    row_id: str,
    input_text: str,
    mode: str,
    iocs: list[dict],
    results: list[dict],
    created_at: str,
) -> _AnalysisInsertRecord:
    """Return the row id and SQL values for persisting an analysis."""
    iocs_json = _encode_json_array(iocs)
    results_json = _encode_json_array(results)
    values = (
        row_id,
        input_text,
        mode,
        iocs_json,
        results_json,
        len(iocs),
        _compute_top_verdict(results),
        created_at,
    )
    return _AnalysisInsertRecord(row_id=row_id, values=values)


def _higher_verdict(first: object, second: object) -> str:
    """Return the higher recognized verdict using summary precedence."""
    first_verdict = (
        first if isinstance(first, str) and first in _VERDICT_PRIORITY else _FALLBACK_VERDICT
    )
    second_verdict = (
        second if isinstance(second, str) and second in _VERDICT_PRIORITY else _FALLBACK_VERDICT
    )
    if _VERDICT_PRIORITY[first_verdict] >= _VERDICT_PRIORITY[second_verdict]:
        return first_verdict
    return second_verdict


def _compute_top_verdict(results: list[dict]) -> str:
    """Derive the highest-precedence saved verdict without hiding conflicts."""
    best = _FALLBACK_VERDICT
    for result in results:
        best = _higher_verdict(best, result.get("verdict"))
        if best == _MAX_VERDICT:
            return best
    return best
