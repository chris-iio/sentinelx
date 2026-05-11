"""Shared local health contract for SentinelX's supported dev loop."""

from __future__ import annotations

from typing import Any, Mapping

HEALTH_PATH = "/api/health"
HEALTH_CHECKS = frozenset({"cache", "history", "registry"})
HEALTH_PAYLOAD = {
    "service": "sentinelx",
    "status": "ok",
    "ready": True,
}


def build_health_payload(checks: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Build a secret-free health payload from cheap dependency checks."""
    normalized_checks: dict[str, dict[str, str]] = {}
    degraded = False

    for name in sorted(HEALTH_CHECKS):
        raw_check = checks.get(name, {})
        status = raw_check.get("status")
        if status not in {"ok", "degraded"}:
            status = "degraded"
        detail = raw_check.get("detail")
        if not isinstance(detail, str) or not detail.strip():
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

    if set(payload) - {"service", "status", "ready", "checks"}:
        return False
    if payload.get("service") != "sentinelx":
        return False
    if payload.get("status") not in {"ok", "degraded"}:
        return False
    if payload.get("ready") is not True:
        return False

    checks = payload.get("checks")
    if checks is None:
        return payload == HEALTH_PAYLOAD
    if not isinstance(checks, dict):
        return False
    if set(checks) != set(HEALTH_CHECKS):
        return False

    for value in checks.values():
        if not isinstance(value, dict):
            return False
        if set(value) - {"status", "detail"}:
            return False
        if value.get("status") not in {"ok", "degraded"}:
            return False
        detail = value.get("detail")
        if not isinstance(detail, str) or not detail or len(detail) > 80:
            return False

    return True
