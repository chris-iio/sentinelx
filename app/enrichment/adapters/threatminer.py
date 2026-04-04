"""ThreatMiner passive DNS and related samples adapter."""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
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


class ThreatMinerAdapter(BaseHTTPAdapter):
    """ThreatMiner multi-call lookup — overrides lookup() for sub-method dispatch."""

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

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
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

    def _build_url(self, ioc: IOC) -> str:
        # Not used — lookup() dispatches to sub-methods with their own URLs.
        raise NotImplementedError(
            "ThreatMinerAdapter.lookup() uses sub-method dispatch, not _build_url"
        )

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        # Not used — sub-methods parse their own responses.
        raise NotImplementedError(
            "ThreatMinerAdapter.lookup() uses sub-method dispatch, not _parse_response"
        )

    def _call(self, ioc: IOC, base_url: str, rt: str) -> dict | EnrichmentError:
        url = f"{base_url}?q={ioc.value}&rt={rt}"
        return safe_request(self._session, url, self._allowed_hosts, ioc, self.name)

    def _lookup_ip(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
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
    """Extract hash strings from a ThreatMiner results list (handles both str and dict entries)."""
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
