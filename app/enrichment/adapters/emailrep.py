"""EmailRep email reputation adapter."""
from __future__ import annotations

from urllib.parse import quote

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult, provider_result
from app.pipeline.models import IOC, IOCType

EMAILREP_BASE = "https://emailrep.io"

_MALICIOUS_FLAGS = (
    "blacklisted",
    "malicious_activity",
    "malicious_activity_recent",
    "credentials_leaked",
    "credentials_leaked_recent",
    "data_breach",
)
_MALICIOUS_FLAG_SET = frozenset(_MALICIOUS_FLAGS)

_RISK_FLAG_FIELDS = (
    *_MALICIOUS_FLAGS,
    "new_domain",
    "suspicious_tld",
    "spam",
    "free_provider",
    "disposable",
)

_NEGATIVE_BOOLEAN_FLAGS = (
    ("deliverable", "deliverable_false"),
    ("valid_mx", "valid_mx_false"),
)
_NO_REPUTATION_VALUES = frozenset(("none", "n/a", "unknown"))
_DETECTION_VERDICTS = frozenset(("malicious", "suspicious"))


class EmailRepAdapter(BaseHTTPAdapter):
    """EmailRep reputation endpoint — email-only, API-key-gated."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.EMAIL,))
    name = "EmailRep"
    requires_api_key = True

    def _build_url(self, ioc: IOC) -> str:
        return f"{EMAILREP_BASE}/{quote(ioc.value, safe='')}"

    def _auth_headers(self) -> dict:
        return {
            "Key": self._api_key,
            "User-Agent": "SentinelX",
            "Accept": "application/json",
        }

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _risk_flags(details: dict) -> tuple[list[str], bool]:
    """Return ordered EmailRep risk flags and whether any are malicious."""
    if not details:
        return [], False
    flags: list[str] = []
    has_malicious_flag = False
    for field in _RISK_FLAG_FIELDS:
        if details.get(field) is True:
            flags.append(field)
            if field in _MALICIOUS_FLAG_SET:
                has_malicious_flag = True
    for field, flag_name in _NEGATIVE_BOOLEAN_FLAGS:
        if details.get(field) is False:
            flags.append(flag_name)
    if details.get("spoofable") is True:
        flags.append("spoofable")
    return flags, has_malicious_flag


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    raw_details = body.get("details")
    details = raw_details if isinstance(raw_details, dict) else {}
    reputation = body.get("reputation") or "none"
    suspicious = bool(body.get("suspicious", False))
    references = body.get("references", 0) or 0
    flags, has_malicious_flag = _risk_flags(details)

    if has_malicious_flag:
        verdict = "malicious"
    elif suspicious or flags or reputation == "low":
        verdict = "suspicious"
    elif reputation in _NO_REPUTATION_VALUES:
        verdict = "no_data"
    else:
        verdict = "clean"

    detection_count = references if verdict in _DETECTION_VERDICTS else 0
    raw_profiles = details.get("profiles") if details else None
    profiles = raw_profiles if isinstance(raw_profiles, list) else []

    raw_stats = {
        "reputation": reputation,
        "suspicious": suspicious,
        "references": references,
        "risk_flags": flags,
        "profiles": profiles,
        "domain_reputation": details.get("domain_reputation"),
        "first_seen": details.get("first_seen"),
        "last_seen": details.get("last_seen"),
        "domain_exists": details.get("domain_exists"),
        "new_domain": details.get("new_domain"),
        "suspicious_tld": details.get("suspicious_tld"),
        "free_provider": details.get("free_provider"),
        "disposable": details.get("disposable"),
        "deliverable": details.get("deliverable"),
        "valid_mx": details.get("valid_mx"),
        "spoofable": details.get("spoofable"),
        "spf_strict": details.get("spf_strict"),
        "dmarc_enforced": details.get("dmarc_enforced"),
    }

    return _emailrep_result(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        scan_date=details.get("last_seen"),
        raw_stats=raw_stats,
    )


def _emailrep_result(
    *,
    ioc: IOC,
    provider: str,
    verdict: str,
    detection_count: int,
    scan_date: str | None,
    raw_stats: dict,
) -> EnrichmentResult:
    return provider_result(
        ioc=ioc,
        provider=provider,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
        scan_date=scan_date,
        raw_stats=raw_stats,
    )
