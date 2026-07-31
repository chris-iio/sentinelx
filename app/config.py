"""Application configuration. Reads from environment variables with validation.

Security requirements addressed:
- SEC-02: API keys read from env vars only
- SEC-03: Fail fast if required API keys are missing
- SEC-16: ALLOWED_API_HOSTS allowlist structure for SSRF prevention (Phase 2)
"""
import os
import secrets
from collections.abc import Mapping, Sequence

from dotenv import load_dotenv

from app.text_utils import has_non_whitespace

# Load .env for development convenience. .env is in .gitignore (SEC-02).
load_dotenv()

SESSION_COOKIE_SAMESITE_VALUES = frozenset(("Strict", "Lax", "None"))


class Config:
    """Production configuration. All security-sensitive values are set here."""

    # SECRET_KEY: required for CSRF and session integrity (SEC-02)
    # Auto-generates if not in env — acceptable for dev; production must set this.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "") or secrets.token_hex(32)

    # Security configuration
    TRUSTED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    MAX_CONTENT_LENGTH: int = 5 * 1024 * 1024  # 5 MB — covers SSH auth.log uploads (SEC-12)
    WTF_CSRF_ENABLED: bool = True

    # SEC-19: SameSite cookie attribute for CSRF defense-in-depth
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # SSRF prevention: allowlist of permitted outbound API hostnames (SEC-16)
    ALLOWED_API_HOSTS: list[str] = [
        "www.virustotal.com",        # VirusTotal (key-required)
        "mb-api.abuse.ch",           # MalwareBazaar (key-required)
        "threatfox-api.abuse.ch",    # ThreatFox (key-required)
        "urlhaus-api.abuse.ch",      # URLhaus (key-required)
        "otx.alienvault.com",        # OTX AlienVault (key-required)
        "api.greynoise.io",          # GreyNoise (key-required)
        "api.abuseipdb.com",         # AbuseIPDB (key-required)
        "emailrep.io",               # EmailRep (key-required)
        "internetdb.shodan.io",      # Shodan InternetDB (zero-auth)
        "ipinfo.io",                 # ipinfo.io GeoIP (zero-auth)
        "hashlookup.circl.lu",       # CIRCL Hashlookup (zero-auth)
        "crt.sh",                    # Certificate Transparency (zero-auth)
        "api.threatminer.org",       # ThreatMiner (zero-auth)
    ]

    # Online enrichment admission controls. These keep one accepted request from
    # exploding into unbounded provider fan-out and local history/cache writes.
    ONLINE_MAX_IOCS: int = int(os.environ.get("ONLINE_MAX_IOCS", "50"))
    ONLINE_MAX_DISPATCHES: int = int(os.environ.get("ONLINE_MAX_DISPATCHES", "200"))
    HISTORY_MAX_ROWS: int = int(os.environ.get("HISTORY_MAX_ROWS", "500"))

    def validate(self) -> None:
        """Validate static configuration invariants at startup.

        Provider API keys are intentionally not validated here because they are
        configured via the Settings page and checked per online request. This
        method validates the security/admission-control values that must always
        be well-formed for the app to run safely.
        """
        validate_config_values({
            "ONLINE_MAX_IOCS": self.ONLINE_MAX_IOCS,
            "ONLINE_MAX_DISPATCHES": self.ONLINE_MAX_DISPATCHES,
            "HISTORY_MAX_ROWS": self.HISTORY_MAX_ROWS,
            "TRUSTED_HOSTS": self.TRUSTED_HOSTS,
            "ALLOWED_API_HOSTS": self.ALLOWED_API_HOSTS,
            "SESSION_COOKIE_SAMESITE": self.SESSION_COOKIE_SAMESITE,
        })


def validate_config_values(values: Mapping[str, object]) -> None:
    """Validate effective runtime configuration values."""
    _validate_positive_int("ONLINE_MAX_IOCS", values.get("ONLINE_MAX_IOCS"))
    _validate_positive_int("ONLINE_MAX_DISPATCHES", values.get("ONLINE_MAX_DISPATCHES"))
    _validate_positive_int("HISTORY_MAX_ROWS", values.get("HISTORY_MAX_ROWS"))
    _validate_non_empty_string_sequence("TRUSTED_HOSTS", values.get("TRUSTED_HOSTS"))
    _validate_non_empty_string_sequence("ALLOWED_API_HOSTS", values.get("ALLOWED_API_HOSTS"))
    _validate_session_cookie_samesite(values.get("SESSION_COOKIE_SAMESITE"))


def _validate_positive_int(name: str, value: object) -> None:
    """Raise ValueError unless *value* is a positive integer."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _validate_session_cookie_samesite(value: object) -> None:
    """Raise ValueError unless *value* is a supported SameSite cookie policy."""
    if value not in SESSION_COOKIE_SAMESITE_VALUES:
        raise ValueError(
            "SESSION_COOKIE_SAMESITE must be one of 'Strict', 'Lax', or 'None'"
        )


def _validate_non_empty_string_sequence(name: str, value: object) -> None:
    """Raise ValueError unless *value* is a non-empty sequence of non-empty strings."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or not value:
        raise ValueError(f"{name} must be a non-empty sequence of hostnames")
    for host in value:
        if not isinstance(host, str) or not has_non_whitespace(host):
            raise ValueError(f"{name} must contain only non-empty hostnames")
