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
import tempfile
from ipaddress import ip_address
from pathlib import Path

from flask import Flask, abort, request
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

    from .config import Config, validate_config_values

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
    app.config["ONLINE_MAX_IOCS"] = config.ONLINE_MAX_IOCS
    app.config["ONLINE_MAX_DISPATCHES"] = config.ONLINE_MAX_DISPATCHES
    app.config["HISTORY_MAX_ROWS"] = config.HISTORY_MAX_ROWS

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

    # Validate the effective app config after overrides are applied.
    validate_config_values(app.config)

    # --- Singleton stores & cached registry ---
    # Create shared CacheStore and HistoryStore once at startup.  Route handlers
    # read current_app.cache_store / current_app.history_store instead of
    # re-instantiating per-request (avoids SQLite connection churn + PRAGMA overhead).
    from .cache.store import CacheStore
    from .enrichment.history_store import HistoryStore

    cache_db_path = app.config.get("CACHE_DB_PATH")
    history_db_path = app.config.get("HISTORY_DB_PATH")
    if app.config.get("TESTING") and (cache_db_path is None or history_db_path is None):
        test_data_dir = Path(tempfile.mkdtemp(prefix="sentinelx-test-"))
        if cache_db_path is None:
            cache_db_path = test_data_dir / "cache.db"
        if history_db_path is None:
            history_db_path = test_data_dir / "history.db"
        app.config["TEST_DATA_DIR"] = str(test_data_dir)

    app.cache_store = CacheStore(Path(cache_db_path) if cache_db_path is not None else None)
    app.history_store = HistoryStore(
        Path(history_db_path) if history_db_path is not None else None,
        max_rows=int(app.config["HISTORY_MAX_ROWS"]),
    )

    from .ctf.store import CtfStore

    ctf_db_path = app.config.get("CTF_DB_PATH")
    if app.config.get("TESTING") and ctf_db_path is None:
        ctf_db_path = Path(app.config["TEST_DATA_DIR"]) / "ctf.db"
    app.ctf_store = CtfStore(Path(ctf_db_path) if ctf_db_path is not None else None)

    from .audit.store import AuditStore

    audit_db_path = app.config.get("AUDIT_DB_PATH")
    if app.config.get("TESTING") and audit_db_path is None:
        audit_db_path = Path(app.config["TEST_DATA_DIR"]) / "audit.db"
    app.audit_store = AuditStore(
        Path(audit_db_path) if audit_db_path is not None else None
    )

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
    from .routes import bp, bp_api
    from .routes.api_audit import bp_api_audit

    app.register_blueprint(bp)
    app.register_blueprint(bp_api)
    app.register_blueprint(bp_api_audit)
    csrf.exempt(bp_api)  # Public analysis JSON does not use session authority.
    # Audit JSON mutates local analyst state and stays CSRF-protected.

    # SEC-22: Sensitive local-admin surfaces must only be reachable from loopback.
    @app.before_request
    def enforce_local_admin_boundary() -> None:
        if _is_local_admin_path(request.path) and not _is_loopback_remote_addr(
            request.remote_addr
        ):
            app.logger.warning(
                "Rejected non-local access to local-admin route %s from %s",
                request.path,
                request.remote_addr or "unknown",
            )
            abort(403)

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
        return "Input too large. Maximum upload size is 5 MB.", 413

    # SEC-21: User-friendly 429 response for rate-limited requests
    @app.errorhandler(429)
    def rate_limit_exceeded(error):  # type: ignore[return]
        return "Too many requests. Please wait a moment and try again.", 429

    # Security invariants enforced by architecture (SEC-08, SEC-13, SEC-14):
    # - Jinja2 autoescaping is ON by default for .html templates (SEC-08)
    # - No shell invocation, eval, or exec anywhere. The single SEC-13
    #   exception is app/ctf/runner.py: allowlisted preset recon profiles
    #   executed via argv lists with validated targets/wordlists, bounded
    #   output, loopback-only.
    # - Offline analysis is stateless. Online analysis history stores the submitted
    #   text locally so an analyst can replay a saved investigation (SEC-14).

    return app


def _is_local_admin_path(path: str) -> bool:
    """Return whether a request path exposes local analyst/admin state."""
    return (
        _path_matches_prefix(path, "/settings")
        or _path_matches_prefix(path, "/history")
        or _path_matches_prefix(path, "/diagnostics")
        or _path_matches_prefix(path, "/enrichment/status")
        or _path_matches_prefix(path, "/api/status")
        or _path_matches_prefix(path, "/api/audit")
        or _path_matches_prefix(path, "/audit")
        or _path_matches_prefix(path, "/ctf")
    )


def _path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def _is_loopback_remote_addr(remote_addr: str | None) -> bool:
    """Return whether Flask's direct peer address is loopback."""
    if remote_addr is None:
        return False
    try:
        return ip_address(remote_addr).is_loopback
    except ValueError:
        return False
