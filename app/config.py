"""Application configuration. Reads from environment variables with validation.

Security requirements addressed:
- SEC-02: API keys read from env vars only
- SEC-03: Fail fast if required API keys are missing
- SEC-16: ALLOWED_API_HOSTS allowlist structure for SSRF prevention (Phase 2)
"""
import os
import secrets

from dotenv import load_dotenv

# Load .env for development convenience. .env is in .gitignore (SEC-02).
load_dotenv()


class Config:
    """Production configuration. All security-sensitive values are set here."""

    # SECRET_KEY: required for CSRF and session integrity (SEC-02)
    # Auto-generates if not in env — acceptable for dev; production must set this.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "") or secrets.token_hex(32)

    # Security configuration
    TRUSTED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    MAX_CONTENT_LENGTH: int = 512 * 1024  # 512 KB — rejects oversize before route runs (SEC-12)
    WTF_CSRF_ENABLED: bool = True

    # SEC-19: SameSite cookie attribute for CSRF defense-in-depth
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # SSRF prevention: allowlist of permitted outbound API hostnames (SEC-16)
    # Phase 2: VirusTotal; Phase 3: MalwareBazaar and ThreatFox (abuse.ch) added.
    # Phase 25: Shodan InternetDB (zero-auth)
    # v6.0 Phase 01-01: ip-api.com GeoIP (zero-auth, HTTP-only free tier)
    # v6.0 Phase 01-01: CIRCL Hashlookup NSRL (zero-auth)
    ALLOWED_API_HOSTS: list[str] = [
        "www.virustotal.com",
        "mb-api.abuse.ch",
        "threatfox-api.abuse.ch",
        "internetdb.shodan.io",    # Phase 25: Shodan InternetDB (zero-auth)
        "urlhaus-api.abuse.ch",    # Phase 03-01: URLhaus (free-key)
        "otx.alienvault.com",      # Phase 03-01: OTX AlienVault (free-key)
        "api.greynoise.io",        # Phase 03-02: GreyNoise Community (free-key)
        "api.abuseipdb.com",       # Phase 03-02: AbuseIPDB (free-key)
        "ip-api.com",              # v6.0 Phase 01-01: ip-api.com GeoIP (zero-auth)
        "hashlookup.circl.lu",     # v6.0 Phase 01-01: CIRCL Hashlookup NSRL (zero-auth)
    ]

    def validate(self) -> None:
        """Validate configuration at startup.

        SEC-03: Currently a no-op. The VT API key is not required at startup
        because it is configured via the Settings page and checked per-request
        in the /analyze route (redirects to /settings if missing).
        """
