"""Application routes.

Phase 1: Placeholder routes. Full implementations come in Plans 02-05.
Templates will be added in Plan 04 (UI implementation).
"""
from flask import Blueprint

bp = Blueprint("main", __name__)


@bp.route("/")
def index():  # type: ignore[return]
    """Home page — placeholder until templates are implemented in Plan 04."""
    return "sentinelx"


@bp.route("/analyze", methods=["POST"])
def analyze():  # type: ignore[return]
    """IOC analysis endpoint — placeholder until pipeline is wired in Plan 03."""
    return "analyze"
