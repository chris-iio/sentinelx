"""Flask application factory.

Security scaffold is established here, before any routes are registered:
- SEC-09: Content Security Policy and other security headers via after_request
- SEC-10: CSRF protection via Flask-WTF CSRFProtect
- SEC-11: TRUSTED_HOSTS rejects requests with unexpected Host header (400)
- SEC-12: MAX_CONTENT_LENGTH caps input size before route handler runs
- SEC-15: debug=False hardcoded — never from environment
"""
from flask import Flask
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()


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
    app.config["TRUSTED_HOSTS"] = config.TRUSTED_HOSTS
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH  # SEC-12
    app.config["WTF_CSRF_ENABLED"] = config.WTF_CSRF_ENABLED  # SEC-10
    app.config["ALLOWED_API_HOSTS"] = config.ALLOWED_API_HOSTS

    # Apply optional test/environment overrides AFTER security defaults are set.
    if config_override:
        app.config.update(config_override)

    # SEC-15: Debug mode is HARDCODED to False after all overrides.
    # Placed last to ensure config_override cannot accidentally enable it.
    app.debug = False

    # SEC-10: CSRF protection on all POST endpoints
    csrf.init_app(app)

    # Validate configuration: fail fast if required env vars missing (SEC-03)
    config.validate()

    # Register blueprint (routes registered after security config is complete)
    from .routes import bp

    app.register_blueprint(bp)

    # SEC-09: Security headers on every response
    @app.after_request
    def set_security_headers(response):  # type: ignore[return]
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    # SEC-12: User-friendly 413 response with size limit stated
    @app.errorhandler(413)
    def request_entity_too_large(error):  # type: ignore[return]
        return "Input too large. Maximum paste size is 512 KB.", 413

    # Security invariants enforced by architecture (SEC-08, SEC-13, SEC-14):
    # - Jinja2 autoescaping is ON by default for .html templates (SEC-08)
    # - No subprocess, shell, or eval/exec calls exist in this codebase (SEC-13)
    # - Pipeline is stateless per request; no raw text stored (SEC-14)

    return app
