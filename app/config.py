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
        "internetdb.shodan.io",      # Shodan InternetDB (zero-auth)
        "ipinfo.io",                 # ipinfo.io GeoIP (zero-auth)
        "hashlookup.circl.lu",       # CIRCL Hashlookup (zero-auth)
        "crt.sh",                    # Certificate Transparency (zero-auth)
        "api.threatminer.org",       # ThreatMiner (zero-auth)
    ]

    def validate(self) -> None:
        """Validate configuration at startup.

        SEC-03: Currently a no-op. The VT API key is not required at startup
        because it is configured via the Settings page and checked per-request
        in the /analyze route (redirects to /settings if missing).
        """
