"""ThreatMiner passive DNS and related samples adapter."""
from __future__ import annotations

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.http_safety import safe_request
from app.enrichment.models import EnrichmentError, EnrichmentResult, error_result, no_data_result
from app.pipeline.models import IOC, IOCType

THREATMINER_BASE_IP = "https://api.threatminer.org/v2/host.php"
THREATMINER_BASE_DOMAIN = "https://api.threatminer.org/v2/domain.php"
THREATMINER_BASE_SAMPLE = "https://api.threatminer.org/v2/sample.php"

# Results caps — keep frontend manageable
_MAX_HOSTS = 25
_MAX_SAMPLES = 20


class ThreatMinerAdapter(BaseHTTPAdapter):
    """ThreatMiner multi-call lookup — overrides lookup() for sub-method dispatch."""

    supported_types: frozenset[IOCType] = frozenset((
        IOCType.IPV4,
        IOCType.IPV6,
        IOCType.DOMAIN,
        IOCType.MD5,
        IOCType.SHA1,
        IOCType.SHA256,
    ))
    name = "ThreatMiner"
    requires_api_key = False

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return error_result(ioc, self.name, "Unsupported type")

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
            return _no_data_result(ioc, self.name)

        # Extract domain field from each result (IP passive DNS: what domains resolved to this IP)
        domains = _extract_field_values(body["results"], "domain", limit=_MAX_HOSTS)

        return _no_data_result(ioc, self.name, {"passive_dns": domains})

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
            ips = _extract_field_values(dns_body["results"], "ip", limit=_MAX_HOSTS)
            if ips:
                raw_stats["passive_dns"] = ips

        # Extract sample hashes from related samples results
        if samples_body.get("status_code") != "404" and samples_body.get("results"):
            samples = _extract_samples(samples_body["results"], limit=_MAX_SAMPLES)
            if samples:
                raw_stats["samples"] = samples

        return _no_data_result(ioc, self.name, raw_stats)

    def _lookup_hash(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        body_or_err = self._call(ioc, THREATMINER_BASE_SAMPLE, "4")
        if isinstance(body_or_err, EnrichmentError):
            return body_or_err
        body = body_or_err

        # Body status_code "404" = no data (HTTP is always 200 for ThreatMiner)
        if body.get("status_code") == "404" or not body.get("results"):
            return _no_data_result(ioc, self.name)

        samples = _extract_samples(body["results"], limit=_MAX_SAMPLES)

        return _no_data_result(ioc, self.name, {"samples": samples})


def _no_data_result(
    ioc: IOC,
    provider_name: str,
    raw_stats: dict | None = None,
) -> EnrichmentResult:
    return no_data_result(ioc, provider_name, raw_stats)


def _extract_field_values(results: list, field_name: str, *, limit: int) -> list[str]:
    """Extract string field values from ThreatMiner result rows up to ``limit``."""
    if limit <= 0:
        return []
    if isinstance(results, list):
        result_count = len(results)
        if result_count == 0:
            return []
        if result_count == 1:
            row = results[0]
            if isinstance(row, dict) and row.get(field_name):
                return [row[field_name]]
            return []
        if result_count == 2:
            values: list[str] = []
            row = results[0]
            if isinstance(row, dict) and row.get(field_name):
                values.append(row[field_name])
                if len(values) >= limit:
                    return values
            row = results[1]
            if isinstance(row, dict) and row.get(field_name):
                values.append(row[field_name])
            return values

    values: list[str] = []
    for row in results:
        if isinstance(row, dict) and row.get(field_name):
            values.append(row[field_name])
            if len(values) >= limit:
                break
    return values


def _extract_samples(results: list, *, limit: int = _MAX_SAMPLES) -> list[str]:
    """Extract hash strings from ThreatMiner results up to ``limit``."""
    if limit <= 0:
        return []
    if isinstance(results, list):
        result_count = len(results)
        if result_count == 0:
            return []
        if result_count == 1:
            row = results[0]
            if isinstance(row, str):
                return [row]
            if isinstance(row, dict):
                for key in row:
                    v = row[key]
                    if isinstance(v, str):
                        return [v]
            return []
        if result_count == 2:
            samples: list[str] = []
            first = results[0]
            if isinstance(first, str):
                samples.append(first)
            elif isinstance(first, dict):
                for key in first:
                    v = first[key]
                    if isinstance(v, str):
                        samples.append(v)
                        break
            if len(samples) >= limit:
                return samples
            second = results[1]
            if isinstance(second, str):
                samples.append(second)
            elif isinstance(second, dict):
                for key in second:
                    v = second[key]
                    if isinstance(v, str):
                        samples.append(v)
                        break
            return samples

    samples: list[str] = []
    for r in results:
        if isinstance(r, str):
            samples.append(r)
        elif isinstance(r, dict):
            # Defensive: extract string values from unexpected dict entries
            for key in r:
                v = r[key]
                if isinstance(v, str):
                    samples.append(v)
                    break  # Only take the first string value per dict
        if len(samples) >= limit:
            break
    return samples
