"""ThreatFox (abuse.ch) API adapter.

Implements IOC enrichment against the ThreatFox API v1 with full HTTP safety controls:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-06: allow_redirects=False on all requests
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call

ThreatFox uses a POST-based JSON API. Hash lookups use "search_hash" query type;
domain/IP/URL lookups use "search_ioc" query type (per ThreatFox API v1 docs).

Confidence-based verdict mapping (per user decision):
  - confidence_level >= 75  ->  verdict="malicious"
  - confidence_level < 75   ->  verdict="suspicious"
  - query_status="no_result" -> verdict="no_data"

No API key required for basic search queries (ThreatFox public search).

Thread safety: a fresh requests.Session is created inside each lookup() call.
"""
from __future__ import annotations

import requests
import requests.exceptions

from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

TF_BASE = "https://threatfox-api.abuse.ch/api/v1/"
CONFIDENCE_THRESHOLD = 75  # >=75 = malicious, <75 = suspicious (per user decision)

# Hash types use a different ThreatFox query endpoint than domain/IP/URL types
_HASH_TYPES = {IOCType.MD5, IOCType.SHA1, IOCType.SHA256}


def _select_best_record(data: list[dict]) -> dict:
    """Return the record with the highest confidence_level.

    ThreatFox may return multiple records for one IOC query. Uses the
    highest-confidence entry for verdict determination.

    Args:
        data: Non-empty list of ThreatFox IOC records.

    Returns:
        The record dict with the maximum confidence_level value.
    """
    return max(data, key=lambda r: r.get("confidence_level", 0))


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    """Parse a ThreatFox API success response into an EnrichmentResult.

    Maps query_status to verdicts:
      - "no_result"  -> verdict="no_data"
      - "ok"         -> confidence-based verdict (>=75 malicious, <75 suspicious)

    For "ok" responses with multiple records, uses the highest-confidence entry.

    Args:
        ioc:  The IOC that was queried.
        body: Parsed JSON from ThreatFox API response.

    Returns:
        EnrichmentResult with verdict, counts, timestamp, and raw stats.
    """
    query_status = body.get("query_status", "")

    if query_status == "no_result":
        return EnrichmentResult(
            ioc=ioc,
            provider="ThreatFox",
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )

    # query_status == "ok" with results
    data: list[dict] = body.get("data", [])
    best = _select_best_record(data)

    confidence_level: int = best.get("confidence_level", 0)
    verdict = "malicious" if confidence_level >= CONFIDENCE_THRESHOLD else "suspicious"

    raw_stats = {
        "threat_type": best.get("threat_type"),
        "malware_printable": best.get("malware_printable"),
        "confidence_level": confidence_level,
        "ioc_type_desc": best.get("ioc_type_desc"),
    }

    return EnrichmentResult(
        ioc=ioc,
        provider="ThreatFox",
        verdict=verdict,
        detection_count=1,
        total_engines=1,
        scan_date=best.get("first_seen"),
        raw_stats=raw_stats,
    )


class TFAdapter:
    """Adapter for the ThreatFox (abuse.ch) API v1.

    Maps IOC types to appropriate ThreatFox query endpoints:
      - Hash types (MD5, SHA1, SHA256): POST {"query": "search_hash", "hash": value}
      - Other types (IP, domain, URL): POST {"query": "search_ioc", "search_term": value}

    Verdict mapping: confidence_level >= 75 -> malicious, < 75 -> suspicious.
    Handles all 7 enrichable IOC types; CVE is not supported by ThreatFox.

    No API key required — basic search queries are public.

    Thread safety: creates a fresh requests.Session per lookup() call.

    Args:
        allowed_hosts: SSRF allowlist — only these hostnames may be contacted.
    """

    supported_types: frozenset[IOCType] = frozenset({
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
        IOCType.DOMAIN, IOCType.IPV4, IOCType.IPV6, IOCType.URL,
    })

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IOC using the ThreatFox API v1.

        Returns EnrichmentError immediately for CVE (not supported by ThreatFox).
        For all other supported types: validates endpoint against the SSRF allowlist,
        constructs the appropriate POST payload, makes a request with full safety
        controls, and parses the response.

        Args:
            ioc: The IOC to look up.

        Returns:
            EnrichmentResult on success or no_result (no_data).
            EnrichmentError on unsupported type, network failure, or HTTP error.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider="ThreatFox", error="Unsupported type"
            )

        try:
            validate_endpoint(TF_BASE, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider="ThreatFox", error=str(exc))

        # Determine payload: hash types use search_hash; others use search_ioc
        if ioc.type in _HASH_TYPES:
            payload = {"query": "search_hash", "hash": ioc.value}
        else:
            payload = {"query": "search_ioc", "search_term": ioc.value}

        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})

        try:
            resp = session.post(
                TF_BASE,
                json=payload,
                timeout=TIMEOUT,          # SEC-04
                allow_redirects=False,    # SEC-06
                stream=True,              # SEC-05 setup
            )
            resp.raise_for_status()
            body = read_limited(resp)   # SEC-05: byte cap enforced here
            return _parse_response(ioc, body)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider="ThreatFox", error="Timeout")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return EnrichmentError(ioc=ioc, provider="ThreatFox", error=f"HTTP {code}")
        except Exception as exc:
            return EnrichmentError(ioc=ioc, provider="ThreatFox", error=str(exc))
