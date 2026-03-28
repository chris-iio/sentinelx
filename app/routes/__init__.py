"""Application routes package.

Registers a single 'main' Blueprint and imports route modules that
attach their handlers to it. This keeps all url_for('main.xxx') references
in templates working without changes.
"""

from flask import Blueprint

bp = Blueprint("main", __name__)

# Import route modules — each attaches @bp.route() decorators to the shared blueprint.
from . import analysis  # noqa: E402, F401
from . import detail  # noqa: E402, F401
from . import enrichment  # noqa: E402, F401
from . import history  # noqa: E402, F401
from . import settings  # noqa: E402, F401

# Separate API blueprint (CSRF-exempt, JSON-only).
from .api import bp_api  # noqa: E402, F401
