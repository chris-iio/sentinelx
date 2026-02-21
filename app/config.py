"""Application configuration. Reads from environment variables with validation.

Security requirements addressed:
- SEC-02: API keys read from env vars only
- SEC-03: Fail fast if required API keys are missing
- SEC-15: DEBUG hardcoded to False
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

    # API keys: read from env only, never from code (SEC-02)
    VIRUSTOTAL_API_KEY: str | None = os.environ.get("VIRUSTOTAL_API_KEY")

    # Security configuration
    TRUSTED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    MAX_CONTENT_LENGTH: int = 512 * 1024  # 512 KB — rejects oversize before route runs (SEC-12)
    WTF_CSRF_ENABLED: bool = True

    # Debug: hardcoded to False — never read from env (SEC-15)
    DEBUG: bool = False

    # SSRF prevention: allowlist of permitted outbound API hostnames (SEC-16)
    # Phase 1 has zero outbound calls. Phase 2 adds entries here.
    ALLOWED_API_HOSTS: list[str] = []

    def validate(self) -> None:
        """Raise ValueError at startup if required env vars are missing.

        SEC-03: Fail fast when online mode is configured but API keys absent.
        Called in create_app() before serving any requests.
        """
        # Phase 1: no required API keys (offline only).
        # Phase 2: uncomment when online mode is added.
        # if self.VIRUSTOTAL_API_KEY is None:
        #     raise ValueError(
        #         "VIRUSTOTAL_API_KEY environment variable is required for online mode. "
        #         "Set it in your .env file or environment."
        #     )
        pass


class TestConfig(Config):
    """Test configuration. Disables CSRF and sets SERVER_NAME for test client."""

    TESTING: bool = True
    WTF_CSRF_ENABLED: bool = False
    SERVER_NAME: str = "localhost"
    # Use a fixed secret key for deterministic test behaviour
    SECRET_KEY: str = "test-secret-key-not-for-production"
