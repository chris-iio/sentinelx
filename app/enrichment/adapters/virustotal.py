"""VirusTotal API v3 adapter — STUB for TDD RED phase.

All methods raise NotImplementedError so tests fail cleanly.
"""
from __future__ import annotations

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentResult, EnrichmentError

VT_BASE = "https://www.virustotal.com/api/v3"
TIMEOUT = (5, 30)
MAX_RESPONSE_BYTES = 1 * 1024 * 1024

ENDPOINT_MAP: dict = {}


def _url_id(url: str) -> str:
    raise NotImplementedError


def _validate_endpoint(url: str, allowed_hosts: list[str]) -> None:
    raise NotImplementedError


def _read_limited(resp) -> dict:
    raise NotImplementedError


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    raise NotImplementedError


def _map_http_error(ioc: IOC, err) -> EnrichmentResult | EnrichmentError:
    raise NotImplementedError


class VTAdapter:
    """Adapter for VirusTotal API v3."""

    def __init__(self, api_key: str, allowed_hosts: list[str]) -> None:
        raise NotImplementedError

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        raise NotImplementedError
