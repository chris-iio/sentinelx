"""IOC detail page route."""

from flask import abort, current_app, render_template

from app import limiter

from . import bp
from .detail_graph import detail_page_route_response


@bp.route("/ioc/<ioc_type>/<path:ioc_value>")
@limiter.limit("30 per minute")
def ioc_detail(ioc_type: str, ioc_value: str) -> str:
    """IOC detail page — shows all cached provider results for a single IOC."""
    return detail_page_route_response(
        current_app.cache_store,
        ioc_type=ioc_type,
        ioc_value=ioc_value,
        abort_request=abort,
        render_template=render_template,
    )
