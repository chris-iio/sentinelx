"""Flask application factory.

Security scaffold is established here, before any routes are registered:
- SEC-09: Content Security Policy and other security headers via after_request
- SEC-10: CSRF protection via Flask-WTF CSRFProtect
- SEC-11: TRUSTED_HOSTS rejects requests with unexpected Host header (400)
- SEC-12: MAX_CONTENT_LENGTH caps input size before route handler runs
- SEC-15: debug=False hardcoded — never from environment
- SEC-21: Rate limiting via Flask-Limiter (in-memory, per-route)
"""
import logging
import os

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

logger = logging.getLogger(__name__)

csrf = CSRFProtect()
# SEC-21: Rate limiting — memory:// is acceptable for single-process local tool.
# limits library has no filesystem backend; Redis/Memcached require infrastructure.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def create_app(config_override: dict | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_override: Optional dict of config values to apply after defaults.
                         Used in tests: create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False})

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # --- Security scaffold (all applied BEFORE routes are registered) ---

    from .config import Config

    config = Config()

    # Apply base config from Config class attributes
    app.config["SECRET_KEY"] = config.SECRET_KEY
    if not os.environ.get("SECRET_KEY"):
        logger.warning(
            "SECRET_KEY not set in environment — using auto-generated key. "
            "Sessions and CSRF tokens will not persist across restarts."
        )
    app.config["TRUSTED_HOSTS"] = config.TRUSTED_HOSTS
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH  # SEC-12
    app.config["WTF_CSRF_ENABLED"] = config.WTF_CSRF_ENABLED  # SEC-10
    app.config["ALLOWED_API_HOSTS"] = config.ALLOWED_API_HOSTS
    app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE  # SEC-19

    # Apply optional test/environment overrides AFTER security defaults are set.
    if config_override:
        app.config.update(config_override)

    # SEC-15: Debug mode is HARDCODED to False after all overrides.
    # Placed last to ensure config_override cannot accidentally enable it.
    app.debug = False

    # SEC-10: CSRF protection on all POST endpoints
    csrf.init_app(app)

    # SEC-21: Rate limiting — in-memory, per-route limits defined in routes.py
    limiter.init_app(app)

    # Validate configuration: fail fast if required env vars missing (SEC-03)
    config.validate()

    # --- Singleton stores & cached registry ---
    # Create shared CacheStore and HistoryStore once at startup.  Route handlers
    # read current_app.cache_store / current_app.history_store instead of
    # re-instantiating per-request (avoids SQLite connection churn + PRAGMA overhead).
    from .cache.store import CacheStore
    from .enrichment.history_store import HistoryStore

    app.cache_store = CacheStore()
    app.history_store = HistoryStore()

    # Registry is built once at startup and cached on the app.  Rebuilt only
    # when settings are saved (settings_post route invalidates it).
    from .enrichment.config_store import ConfigStore
    from .enrichment.setup import build_registry

    config_store = ConfigStore()
    allowed_hosts = app.config.get("ALLOWED_API_HOSTS", [])
    app.registry = build_registry(allowed_hosts=allowed_hosts, config_store=config_store)

    # Static asset cache-control (24 hours) — avoids re-downloading ~568KB
    # of fonts/JS/CSS on every page navigation.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400

    # Register blueprint (routes registered after security config is complete)
    from .routes import bp

    app.register_blueprint(bp)

    # SEC-09: Security headers on every response
    @app.after_request
    def set_security_headers(response):  # type: ignore[return]
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "connect-src 'self'; "
            "img-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "no-referrer"
        # SEC-20: Restrict browser features not needed by this app
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        return response

    # SEC-12: User-friendly 413 response with size limit stated
    @app.errorhandler(413)
    def request_entity_too_large(error):  # type: ignore[return]
        return "Input too large. Maximum paste size is 512 KB.", 413

    # SEC-21: User-friendly 429 response for rate-limited requests
    @app.errorhandler(429)
    def rate_limit_exceeded(error):  # type: ignore[return]
        return "Too many requests. Please wait a moment and try again.", 429

    # Security invariants enforced by architecture (SEC-08, SEC-13, SEC-14):
    # - Jinja2 autoescaping is ON by default for .html templates (SEC-08)
    # - No subprocess, shell, or eval/exec calls exist in this codebase (SEC-13)
    # - Pipeline is stateless per request; no raw text stored (SEC-14)

    return app
