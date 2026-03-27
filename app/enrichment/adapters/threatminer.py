"""ThreatMiner passive DNS and related samples adapter.

Implements multi-IOC-type enrichment via the ThreatMiner API v2 (api.threatminer.org).
Provides passive DNS history (IP/domain lookups) and related malware sample hashes
(domain/hash lookups) without requiring an API key. Delegates all HTTP safety controls
to safe_request() in http_safety.py.

ThreatMiner API v2 behavior:
  - GET https://api.threatminer.org/v2/host.php?q={ip}&rt=2
    -> IP passive DNS (domains that resolved to IP)
  - GET https://api.threatminer.org/v2/domain.php?q={domain}&rt=2
    -> Domain passive DNS (IPs domain resolved to)
  - GET https://api.threatminer.org/v2/domain.php?q={domain}&rt=4 -> Domain related samples
  - GET https://api.threatminer.org/v2/sample.php?q={hash}&rt=4   -> Hash related samples
  - HTTP 200 + body status_code "200": Results found
  - HTTP 200 + body status_code "404": No results -> verdict=no_data (NOT an HTTP error)
  - HTTP 429: Rate limited (>10 req/min) -> EnrichmentError("HTTP 429")
  - HTTP 403: Blocked/IP ban -> EnrichmentError("HTTP 403")
  - Timeout: -> EnrichmentError("Request timed out")

CRITICAL: ThreatMiner always returns HTTP 200, even for "not found" responses.
The body's status_code field (a string "404", not int) is the authoritative signal.

Verdict semantics:
  - All responses: verdict=no_data — passive DNS is informational context, not a threat signal
  - detection_count=0, total_engines=0, scan_date=None always

Results caps:
  - _MAX_HOSTS=25: passive_dns list (both IP and domain lookups)
  - _MAX_SAMPLES=20: samples list (both domain and hash lookups)

Thread safety: a persistent requests.Session is created in __init__ and reused across
_call() invocations (TCP connection pooling).
"""
from __future__ import annotations

import logging

import requests

from app.enrichment.http_safety import safe_request
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

THREATMINER_BASE_IP = "https://api.threatminer.org/v2/host.php"
THREATMINER_BASE_DOMAIN = "https://api.threatminer.org/v2/domain.php"
THREATMINER_BASE_SAMPLE = "https://api.threatminer.org/v2/sample.php"

# Results caps — keep frontend manageable
_MAX_HOSTS = 25
_MAX_SAMPLES = 20


class ThreatMinerAdapter:
    """Adapter for the ThreatMiner API v2.

    Supports IP, domain, and hash IOC lookups via the zero-auth ThreatMiner public API.
    Returns passive DNS history (domains for IPs, IPs for domains) and related malware
    sample hashes without requiring an API key.

    IOC type routing:
      - IPV4/IPV6 -> host.php rt=2 (passive DNS: what domains resolved to this IP)
      - DOMAIN    -> domain.php rt=2 (passive DNS: IPs this domain resolved to)
                  + domain.php rt=4 (related samples: malware associated with this domain)
                  Results merged into single raw_stats dict.
      - MD5/SHA1/SHA256 -> sample.php rt=4 (related samples: hashes related to this sample)

    All responses produce verdict=no_data — ThreatMiner data is
    analyst context, not threat detection.

    Rate limit: 10 requests/minute. Exceeding returns HTTP 429 -> EnrichmentError("HTTP 429").
    For domain IOCs (2 calls), if the first call hits 429, the second is skipped.

    No API key required — ThreatMiner is fully public.

    Thread safety: uses a persistent requests.Session (self._session) created in __init__.
    The session is reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
                       Must include "api.threatminer.org" for production use.
    """

    supported_types: frozenset[IOCType] = frozenset({
        IOCType.IPV4,
        IOCType.IPV6,
        IOCType.DOMAIN,
        IOCType.MD5,
        IOCType.SHA1,
        IOCType.SHA256,
    })
    name = "ThreatMiner"
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts
        self._session = requests.Session()

    def is_configured(self) -> bool:
        """Always returns True -- ThreatMiner requires no API key."""
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IOC via the ThreatMiner API v2.

        Routes to the appropriate ThreatMiner endpoint based on IOC type:
          - IP (IPv4/IPv6): host.php rt=2 -> passive DNS (domains that resolved to this IP)
          - Domain: domain.php rt=2+rt=4 -> merged passive DNS + related samples
          - Hash (MD5/SHA1/SHA256): sample.php rt=4 -> related sample hashes

        Returns EnrichmentError immediately for unsupported IOC types.

        Args:
            ioc: The IOC to look up.

        Returns:
            EnrichmentResult on success (always verdict=no_data).
            EnrichmentError on unsupported type, SSRF block, rate limit, or network failure.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type"
            )

        if ioc.type in (IOCType.IPV4, IOCType.IPV6):
            return self._lookup_ip(ioc)
        elif ioc.type == IOCType.DOMAIN:
            return self._lookup_domain(ioc)
        else:
            return self._lookup_hash(ioc)

    def _call(self, ioc: IOC, base_url: str, rt: str) -> dict | EnrichmentError:
        """Make one ThreatMiner API call via safe_request().

        Validates the endpoint against the SSRF allowlist, then makes a GET request
        with the IOC value as the 'q' parameter and the resource type as 'rt'.

        Args:
            ioc:      The IOC being queried (used for SSRF check and error construction).
            base_url: The ThreatMiner base endpoint URL (host.php, domain.php, sample.php).
            rt:       The resource type parameter ("2" for passive DNS, "4" for related samples).

        Returns:
            Parsed JSON dict on success.
            EnrichmentError on SSRF block, HTTP error, timeout, or unexpected failure.
        """
        url = f"{base_url}?q={ioc.value}&rt={rt}"
        return safe_request(self._session, url, self._allowed_hosts, ioc, self.name)

    def _lookup_ip(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Look up passive DNS history for an IP address.

        Queries host.php rt=2 for a list of domains that historically resolved to this IP.

        Args:
            ioc: An IPV4 or IPV6 IOC.

        Returns:
            EnrichmentResult with raw_stats={"passive_dns": ["domain1.com", ...]}
            (capped at _MAX_HOSTS).
            raw_stats={} if body status_code is "404" or results are empty.
            EnrichmentError on network/SSRF failure.
        """
        body_or_err = self._call(ioc, THREATMINER_BASE_IP, "2")
        if isinstance(body_or_err, EnrichmentError):
            return body_or_err
        body = body_or_err

        # Body status_code "404" = no data (HTTP is always 200 for ThreatMiner)
        if body.get("status_code") == "404" or not body.get("results"):
            return EnrichmentResult(
                ioc=ioc,
                provider=self.name,
                verdict="no_data",
                detection_count=0,
                total_engines=0,
                scan_date=None,
                raw_stats={},
            )

        # Extract domain field from each result (IP passive DNS: what domains resolved to this IP)
        domains = [
            r["domain"]
            for r in body["results"]
            if isinstance(r, dict) and r.get("domain")
        ][:_MAX_HOSTS]

        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={"passive_dns": domains},
        )

    def _lookup_domain(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Look up passive DNS history and related samples for a domain.

        Makes TWO sequential API calls:
          1. domain.php rt=2 -> IPs this domain historically resolved to
          2. domain.php rt=4 -> related malware sample hashes

        If the first call returns an error (including HTTP 429), the second call is skipped
        and the error is returned immediately. If one call returns body status_code "404",
        that data is omitted from the merged result; the other call's data is still used.

        Args:
            ioc: A DOMAIN IOC.

        Returns:
            Merged EnrichmentResult with raw_stats containing any non-empty data
            from passive_dns and/or samples. raw_stats={} if both calls return "404".
            EnrichmentError if any API call fails with a hard error (429, 403, timeout, etc.).
        """
        # First call: passive DNS (rt=2)
        body_or_err = self._call(ioc, THREATMINER_BASE_DOMAIN, "2")
        if isinstance(body_or_err, EnrichmentError):
            return body_or_err
        dns_body = body_or_err

        # Second call: related samples (rt=4)
        samples_or_err = self._call(ioc, THREATMINER_BASE_DOMAIN, "4")
        if isinstance(samples_or_err, EnrichmentError):
            return samples_or_err
        samples_body = samples_or_err

        # Build merged raw_stats — only include data that actually exists
        raw_stats: dict = {}

        # Extract IPs from passive DNS results (domain direction: domain -> IP)
        if dns_body.get("status_code") != "404" and dns_body.get("results"):
            ips = [
                r["ip"]
                for r in dns_body["results"]
                if isinstance(r, dict) and r.get("ip")
            ][:_MAX_HOSTS]
            if ips:
                raw_stats["passive_dns"] = ips

        # Extract sample hashes from related samples results
        if samples_body.get("status_code") != "404" and samples_body.get("results"):
            samples = _extract_samples(samples_body["results"])[:_MAX_SAMPLES]
            if samples:
                raw_stats["samples"] = samples

        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats=raw_stats,
        )

    def _lookup_hash(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Look up related malware samples for a hash IOC.

        Queries sample.php rt=4 for a list of related malware sample hashes.
        Results are typically plain SHA-256 strings; defensive handling supports
        dict entries as well (extracting string values from them).

        Args:
            ioc: An MD5, SHA1, or SHA256 IOC.

        Returns:
            EnrichmentResult with raw_stats={"samples": ["sha256hash", ...]}
            (capped at _MAX_SAMPLES).
            raw_stats={} if body status_code is "404" or results are empty.
            EnrichmentError on network/SSRF failure.
        """
        body_or_err = self._call(ioc, THREATMINER_BASE_SAMPLE, "4")
        if isinstance(body_or_err, EnrichmentError):
            return body_or_err
        body = body_or_err

        # Body status_code "404" = no data (HTTP is always 200 for ThreatMiner)
        if body.get("status_code") == "404" or not body.get("results"):
            return EnrichmentResult(
                ioc=ioc,
                provider=self.name,
                verdict="no_data",
                detection_count=0,
                total_engines=0,
                scan_date=None,
                raw_stats={},
            )

        samples = _extract_samples(body["results"])[:_MAX_SAMPLES]

        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={"samples": samples},
        )


def _extract_samples(results: list) -> list[str]:
    """Extract sample hash strings from a ThreatMiner results list.

    ThreatMiner related samples results are typically plain string lists.
    Defensively handles dict entries by extracting string values from them.

    Args:
        results: The "results" array from a ThreatMiner rt=4 API response.

    Returns:
        List of hash strings extracted from the results.
    """
    samples: list[str] = []
    for r in results:
        if isinstance(r, str):
            samples.append(r)
        elif isinstance(r, dict):
            # Defensive: extract string values from unexpected dict entries
            for v in r.values():
                if isinstance(v, str):
                    samples.append(v)
                    break  # Only take the first string value per dict
    return samples
