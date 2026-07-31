"""Shared route JSON payload normalization helpers."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class JsonRequest(Protocol):
    """Minimal request protocol for JSON body extraction."""

    def get_json(self, *, silent: bool = False) -> object: ...


def json_mapping_payload(request_obj: JsonRequest) -> Mapping[str, object] | None:
    """Return the decoded JSON object payload, rejecting absent/non-object JSON."""
    payload = request_obj.get_json(silent=True)
    if not isinstance(payload, Mapping):
        return None
    return payload
