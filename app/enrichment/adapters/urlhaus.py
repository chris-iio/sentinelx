"""URLhaus URL/host/payload lookup adapter (abuse.ch)."""
from __future__ import annotations

from types import MappingProxyType
from typing import NamedTuple

from .abusech import abusech_query_status
from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, provider_result
from app.pipeline.models import IOC, IOCType

URLHAUS_BASE = "https://urlhaus-api.abuse.ch"

# Maps IOCType to (url_path, body_key) for POST requests
_ENDPOINT_MAP = MappingProxyType({
    IOCType.URL: ("/v1/url/", "url"),
    IOCType.IPV4: ("/v1/host/", "host"),
    IOCType.IPV6: ("/v1/host/", "host"),
    IOCType.DOMAIN: ("/v1/host/", "host"),
    IOCType.MD5: ("/v1/payload/", "md5_hash"),
    IOCType.SHA256: ("/v1/payload/", "sha256_hash"),
})


class UrlhausSignals(NamedTuple):
    query_status: str
    urls_count: int
    tags: object
    blacklists: dict
    signature: object


def _urlhaus_signals(body: dict) -> UrlhausSignals:
    raw_blacklists = body.get("blacklists")
    blacklists = raw_blacklists if isinstance(raw_blacklists, dict) else {}
    return UrlhausSignals(
        query_status=abusech_query_status(body),
        urls_count=body.get("urls_count", 0) or 0,
        tags=body.get("tags"),
        blacklists=blacklists,
        signature=body.get("signature"),
    )


class URLhausAdapter(BaseHTTPAdapter):
    """URLhaus multi-endpoint lookup — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset(_ENDPOINT_MAP)
    name = "URLhaus"
    requires_api_key = True
    _http_method = "POST"

    def _build_url(self, ioc: IOC) -> str:
        url_path, _ = _ENDPOINT_MAP[ioc.type]
        return f"{URLHAUS_BASE}{url_path}"

    def _auth_headers(self) -> dict:
        return {
            "Auth-Key": self._api_key,
            "Accept": "application/json",
        }

    def _build_request_body(self, ioc: IOC) -> tuple[dict | None, dict | None]:
        # Form-encoded POST: data dict, no JSON payload
        _, body_key = _ENDPOINT_MAP[ioc.type]
        return ({body_key: ioc.value}, None)

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    signals = _urlhaus_signals(body)
    verdict, detection_count = _urlhaus_verdict(signals.query_status, signals.urls_count)

    return _urlhaus_result(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        raw_stats=_urlhaus_raw_stats(
            signals=signals,
        ),
    )


def _urlhaus_verdict(query_status: str, urls_count: int) -> tuple[str, int]:
    if query_status == "is_listed":
        return ("malicious", 1)
    if query_status == "ok" and urls_count > 0:
        return ("malicious", urls_count)
    return ("no_data", 0)


def _urlhaus_raw_stats(*, signals: UrlhausSignals) -> dict:
    return {
        "query_status": signals.query_status,
        "urls_count": signals.urls_count,
        "tags": signals.tags,
        "blacklists": signals.blacklists,
        "signature": signals.signature,
    }


def _urlhaus_result(
    *,
    ioc: IOC,
    provider: str,
    verdict: str,
    detection_count: int,
    raw_stats: dict,
) -> EnrichmentResult:
    return provider_result(
        ioc=ioc,
        provider=provider,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
        scan_date=None,
        raw_stats=raw_stats,
    )
