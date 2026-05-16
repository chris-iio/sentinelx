"""Shared local health contract for SentinelX's supported dev loop."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from app.text_utils import has_non_whitespace

HEALTH_PATH = "/api/health"
HEALTH_CHECK_ORDER = ("cache", "history", "registry")
HEALTH_CHECKS = frozenset(HEALTH_CHECK_ORDER)
HEALTH_STATUSES = frozenset(("ok", "degraded"))
HEALTH_PAYLOAD_KEYS = frozenset(("service", "status", "ready", "checks"))
HEALTH_CHECK_VALUE_KEYS = frozenset(("status", "detail"))
HEALTH_PAYLOAD: Mapping[str, Any] = MappingProxyType({
    "service": "sentinelx",
    "status": "ok",
    "ready": True,
})
_EMPTY_HEALTH_CHECK: Mapping[str, Any] = MappingProxyType({})


def _has_only_keys(mapping: dict[str, Any], allowed_keys: frozenset[str]) -> bool:
    for key in mapping:
        if key not in allowed_keys:
            return False
    return True


def _has_exact_keys(mapping: dict[str, Any], expected_keys: frozenset[str]) -> bool:
    if len(mapping) != len(expected_keys):
        return False
    for key in expected_keys:
        if key not in mapping:
            return False
    return True


def build_health_payload(checks: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Build a secret-free health payload from cheap dependency checks."""
    normalized_checks: dict[str, dict[str, str]] = {}
    degraded = False

    for name in HEALTH_CHECK_ORDER:
        raw_check = checks.get(name, _EMPTY_HEALTH_CHECK)
        status = raw_check.get("status")
        if status not in HEALTH_STATUSES:
            status = "degraded"
        detail = raw_check.get("detail")
        if not isinstance(detail, str) or not has_non_whitespace(detail):
            detail = "ok" if status == "ok" else "unavailable"
        normalized_checks[name] = {
            "status": status,
            "detail": detail[:80],
        }
        degraded = degraded or status == "degraded"

    return {
        "service": "sentinelx",
        "status": "degraded" if degraded else "ok",
        "ready": True,
        "checks": normalized_checks,
    }


def is_valid_health_payload(payload: object) -> bool:
    """Return whether a payload matches the secret-free health schema."""
    if not isinstance(payload, dict):
        return False

    if not _has_only_keys(payload, HEALTH_PAYLOAD_KEYS):
        return False
    if payload.get("service") != "sentinelx":
        return False
    if payload.get("status") not in HEALTH_STATUSES:
        return False
    if payload.get("ready") is not True:
        return False

    checks = payload.get("checks")
    if checks is None:
        return payload == HEALTH_PAYLOAD
    if not isinstance(checks, dict):
        return False
    if not _has_exact_keys(checks, HEALTH_CHECKS):
        return False

    for name in HEALTH_CHECK_ORDER:
        value = checks[name]
        if not isinstance(value, dict):
            return False
        if not _has_only_keys(value, HEALTH_CHECK_VALUE_KEYS):
            return False
        if value.get("status") not in HEALTH_STATUSES:
            return False
        detail = value.get("detail")
        if not isinstance(detail, str) or not detail or len(detail) > 80:
            return False

    return True
