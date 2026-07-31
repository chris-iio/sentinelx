"""EmailRep email reputation adapter."""
from __future__ import annotations

from typing import NamedTuple
from urllib.parse import quote

from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, provider_result
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


class EmailRepSignals(NamedTuple):
    details: dict
    reputation: str
    suspicious: bool
    references: int


def _emailrep_signals(body: dict) -> EmailRepSignals:
    raw_details = body.get("details")
    details = raw_details if isinstance(raw_details, dict) else {}
    return EmailRepSignals(
        details=details,
        reputation=body.get("reputation") or "none",
        suspicious=bool(body.get("suspicious", False)),
        references=body.get("references", 0) or 0,
    )


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
    has_malicious_flag = (
        _append_positive_risk_flag(flags, details, "blacklisted", True)
        or has_malicious_flag
    )
    has_malicious_flag = (
        _append_positive_risk_flag(flags, details, "malicious_activity", True)
        or has_malicious_flag
    )
    has_malicious_flag = _append_positive_risk_flag(
        flags,
        details,
        "malicious_activity_recent",
        True,
    ) or has_malicious_flag
    has_malicious_flag = (
        _append_positive_risk_flag(flags, details, "credentials_leaked", True)
        or has_malicious_flag
    )
    has_malicious_flag = _append_positive_risk_flag(
        flags,
        details,
        "credentials_leaked_recent",
        True,
    ) or has_malicious_flag
    has_malicious_flag = (
        _append_positive_risk_flag(flags, details, "data_breach", True)
        or has_malicious_flag
    )
    _append_positive_risk_flag(flags, details, "new_domain", False)
    _append_positive_risk_flag(flags, details, "suspicious_tld", False)
    _append_positive_risk_flag(flags, details, "spam", False)
    _append_positive_risk_flag(flags, details, "free_provider", False)
    _append_positive_risk_flag(flags, details, "disposable", False)
    _append_negative_risk_flag(flags, details, "deliverable", "deliverable_false")
    _append_negative_risk_flag(flags, details, "valid_mx", "valid_mx_false")
    _append_positive_risk_flag(flags, details, "spoofable", False)
    return flags, has_malicious_flag


def _append_positive_risk_flag(
    flags: list[str],
    details: dict,
    field: str,
    malicious: bool,
) -> bool:
    if details.get(field) is True:
        _append_risk_flag(flags, field)
        return malicious
    return False


def _append_negative_risk_flag(
    flags: list[str],
    details: dict,
    field: str,
    flag_name: str,
) -> None:
    if details.get(field) is False:
        _append_risk_flag(flags, flag_name)


def _append_risk_flag(flags: list[str], flag_name: str) -> None:
    flags.append(flag_name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    signals = _emailrep_signals(body)
    flags, has_malicious_flag = _risk_flags(signals.details)
    verdict = _emailrep_verdict(
        reputation=signals.reputation,
        suspicious=signals.suspicious,
        flags=flags,
        has_malicious_flag=has_malicious_flag,
    )

    return _emailrep_result(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=_emailrep_detection_count(verdict, signals.references),
        scan_date=signals.details.get("last_seen"),
        raw_stats=_emailrep_raw_stats(
            details=signals.details,
            reputation=signals.reputation,
            suspicious=signals.suspicious,
            references=signals.references,
            flags=flags,
        ),
    )


def _emailrep_verdict(
    *,
    reputation: str,
    suspicious: bool,
    flags: list[str],
    has_malicious_flag: bool,
) -> str:
    if has_malicious_flag:
        return "malicious"
    if suspicious or flags or reputation == "low":
        return "suspicious"
    if reputation in _NO_REPUTATION_VALUES:
        return "no_data"
    return "clean"


def _emailrep_detection_count(verdict: str, references: int) -> int:
    if verdict in _DETECTION_VERDICTS:
        return references
    return 0


def _emailrep_profiles(details: dict) -> list:
    raw_profiles = details.get("profiles") if details else None
    return raw_profiles if isinstance(raw_profiles, list) else []


def _emailrep_raw_stats(
    *,
    details: dict,
    reputation: str,
    suspicious: bool,
    references: int,
    flags: list[str],
) -> dict:
    return {
        "reputation": reputation,
        "suspicious": suspicious,
        "references": references,
        "risk_flags": flags,
        "profiles": _emailrep_profiles(details),
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
