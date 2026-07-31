"""ThreatMiner passive DNS and related samples adapter."""
from __future__ import annotations

from .base import BaseHTTPAdapter
from ..http_safety import safe_request
from ..models import EnrichmentError, EnrichmentResult, error_result, no_data_result
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
        return safe_request(
            self._session,
            _threatminer_request_url(base_url, ioc.value, rt),
            self._allowed_hosts,
            ioc,
            self.name,
        )

    def _lookup_ip(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        body_or_err = self._call(ioc, THREATMINER_BASE_IP, "2")
        if isinstance(body_or_err, EnrichmentError):
            return body_or_err
        body = body_or_err

        # Body status_code "404" = no data (HTTP is always 200 for ThreatMiner)
        if not _has_results(body):
            return _no_data_result(ioc, self.name)

        # Extract domain field from each result (IP passive DNS: what domains resolved to this IP)
        return _no_data_result(
            ioc,
            self.name,
            _passive_dns_raw_stats(body, field_name="domain"),
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

        return _no_data_result(
            ioc,
            self.name,
            _domain_raw_stats(dns_body=dns_body, samples_body=samples_body),
        )

    def _lookup_hash(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        body_or_err = self._call(ioc, THREATMINER_BASE_SAMPLE, "4")
        if isinstance(body_or_err, EnrichmentError):
            return body_or_err
        body = body_or_err

        # Body status_code "404" = no data (HTTP is always 200 for ThreatMiner)
        if not _has_results(body):
            return _no_data_result(ioc, self.name)

        return _no_data_result(ioc, self.name, _samples_raw_stats(body))


def _no_data_result(
    ioc: IOC,
    provider_name: str,
    raw_stats: dict | None = None,
) -> EnrichmentResult:
    return no_data_result(ioc, provider_name, raw_stats)


def _threatminer_request_url(base_url: str, value: str, rt: str) -> str:
    return f"{base_url}?q={value}&rt={rt}"


def _has_results(body: dict) -> bool:
    return body.get("status_code") != "404" and bool(body.get("results"))


def _passive_dns_raw_stats(body: dict, *, field_name: str) -> dict:
    return {
        "passive_dns": _extract_field_values(
            body["results"],
            field_name,
            limit=_MAX_HOSTS,
        ),
    }


def _samples_raw_stats(body: dict) -> dict:
    return {"samples": _extract_samples(body["results"], limit=_MAX_SAMPLES)}


def _domain_raw_stats(*, dns_body: dict, samples_body: dict) -> dict:
    raw_stats: dict = {}
    append_domain_passive_dns(raw_stats, dns_body)
    append_domain_samples(raw_stats, samples_body)
    return raw_stats


def append_domain_passive_dns(raw_stats: dict, dns_body: dict) -> None:
    if _has_results(dns_body):
        passive_dns = _passive_dns_raw_stats(dns_body, field_name="ip")["passive_dns"]
        if passive_dns:
            raw_stats["passive_dns"] = passive_dns


def append_domain_samples(raw_stats: dict, samples_body: dict) -> None:
    if _has_results(samples_body):
        samples = _samples_raw_stats(samples_body)["samples"]
        if samples:
            raw_stats["samples"] = samples


def _append_field_value(values: list[str], row: object, field_name: str, *, limit: int) -> bool:
    """Append one requested ThreatMiner field value and return whether the cap is reached."""
    if isinstance(row, dict) and row.get(field_name):
        values.append(row[field_name])
    return len(values) >= limit


def _extract_field_values(results: list, field_name: str, *, limit: int) -> list[str]:
    """Extract string field values from ThreatMiner result rows up to ``limit``."""
    if limit <= 0:
        return []
    if isinstance(results, list):
        result_count = len(results)
        if result_count == 0:
            return []
        if result_count == 1:
            values: list[str] = []
            _append_field_value(values, results[0], field_name, limit=limit)
            return values
        if result_count == 2:
            values: list[str] = []
            if _append_field_value(values, results[0], field_name, limit=limit):
                return values
            _append_field_value(values, results[1], field_name, limit=limit)
            return values
        if result_count == 3:
            values: list[str] = []
            if _append_field_value(values, results[0], field_name, limit=limit):
                return values
            if _append_field_value(values, results[1], field_name, limit=limit):
                return values
            _append_field_value(values, results[2], field_name, limit=limit)
            return values
        if result_count == 4:
            values: list[str] = []
            if _append_field_value(values, results[0], field_name, limit=limit):
                return values
            if _append_field_value(values, results[1], field_name, limit=limit):
                return values
            if _append_field_value(values, results[2], field_name, limit=limit):
                return values
            _append_field_value(values, results[3], field_name, limit=limit)
            return values

    values: list[str] = []
    for row in results:
        if _append_field_value(values, row, field_name, limit=limit):
            break
    return values


def _append_sample_value(samples: list[str], row: object, *, limit: int) -> bool:
    """Append one ThreatMiner sample value and return whether the cap is reached."""
    if isinstance(row, str):
        _append_sample_string(samples, row)
    elif isinstance(row, dict):
        for key in row:
            v = row[key]
            if isinstance(v, str):
                _append_sample_string(samples, v)
                break
    return len(samples) >= limit


def _append_sample_string(samples: list[str], value: str) -> None:
    samples.append(value)


def _extract_samples(results: list, *, limit: int = _MAX_SAMPLES) -> list[str]:
    """Extract hash strings from ThreatMiner results up to ``limit``."""
    if limit <= 0:
        return []
    if isinstance(results, list):
        result_count = len(results)
        if result_count == 0:
            return []
        if result_count == 1:
            samples: list[str] = []
            _append_sample_value(samples, results[0], limit=limit)
            return samples
        if result_count == 2:
            samples: list[str] = []
            if _append_sample_value(samples, results[0], limit=limit):
                return samples
            _append_sample_value(samples, results[1], limit=limit)
            return samples
        if result_count == 3:
            samples: list[str] = []
            if _append_sample_value(samples, results[0], limit=limit):
                return samples
            if _append_sample_value(samples, results[1], limit=limit):
                return samples
            _append_sample_value(samples, results[2], limit=limit)
            return samples
        if result_count == 4:
            samples: list[str] = []
            if _append_sample_value(samples, results[0], limit=limit):
                return samples
            if _append_sample_value(samples, results[1], limit=limit):
                return samples
            if _append_sample_value(samples, results[2], limit=limit):
                return samples
            _append_sample_value(samples, results[3], limit=limit)
            return samples

    samples: list[str] = []
    for r in results:
        if _append_sample_value(samples, r, limit=limit):
            break
    return samples
