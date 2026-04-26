"""Shared local health contract for SentinelX's supported dev loop."""

HEALTH_PATH = "/api/health"
HEALTH_PAYLOAD = {
    "service": "sentinelx",
    "status": "ok",
    "ready": True,
}
