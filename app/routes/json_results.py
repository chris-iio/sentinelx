"""Shared JSON route result application helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class JsonResult:
    """JSON response payload and HTTP status."""

    payload: dict[str, Any]
    status: int


class JsonRouteResult(Protocol):
    payload: dict[str, Any]
    status: int


def apply_json_result(
    result: JsonRouteResult,
    *,
    jsonify_response: Callable[[dict[str, Any]], Any],
) -> Any:
    """Apply a JSON result through Flask response formatting."""
    return jsonify_response(result.payload), result.status
