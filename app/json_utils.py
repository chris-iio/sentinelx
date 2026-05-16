"""Shared JSON literals and lightweight serialization helpers."""
from __future__ import annotations

import json

EMPTY_JSON_ARRAY = "[]"
EMPTY_JSON_OBJECT = "{}"


def encode_json_object(payload: dict) -> str:
    """Serialize a JSON object, skipping encoder work for an empty dict."""
    if not payload:
        return EMPTY_JSON_OBJECT
    return json.dumps(payload)


def decode_json_object(payload_json: str) -> dict:
    """Deserialize a JSON object, skipping decoder work for the empty literal."""
    if payload_json == EMPTY_JSON_OBJECT:
        return {}
    return json.loads(payload_json)


def encode_json_array(payload: list[dict]) -> str:
    """Serialize a JSON array, skipping encoder work for an empty list."""
    if not payload:
        return EMPTY_JSON_ARRAY
    return json.dumps(payload)


def decode_json_array(payload_json: str) -> list[dict]:
    """Deserialize a JSON array, skipping decoder work for the empty literal."""
    if payload_json == EMPTY_JSON_ARRAY:
        return []
    return json.loads(payload_json)
