"""History routes: list and reload past analyses."""

from flask import abort, current_app, render_template

from app import limiter

from . import bp
from .history_replay import (
    history_detail_route_response,
    history_list_route_response,
)


@bp.route("/history")
@limiter.limit("30 per minute")
def history_list():
    """List recent analyses."""
    return history_list_route_response(
        current_app.history_store,
        render_template=render_template,
    )


@bp.route("/history/<analysis_id>")
@limiter.limit("30 per minute")
def history_detail(analysis_id: str):
    """Reload a past analysis from history."""
    return history_detail_route_response(
        current_app.history_store,
        analysis_id,
        abort_request=abort,
        render_template=render_template,
    )
