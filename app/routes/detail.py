"""IOC detail page route."""

from flask import abort, current_app, render_template

from app import limiter
from app.pipeline.models import IOCType

from . import bp


@bp.route("/ioc/<ioc_type>/<path:ioc_value>")
@limiter.limit("30 per minute")
def ioc_detail(ioc_type: str, ioc_value: str) -> str:
    """IOC detail page — shows all cached provider results for a single IOC."""
    valid_types = {t.value for t in IOCType}
    if ioc_type not in valid_types:
        abort(404)

    cache = current_app.cache_store
    provider_results = cache.get_all_for_ioc(ioc_value, ioc_type)

    graph_nodes = [
        {"id": "ioc", "label": ioc_value, "verdict": "ioc", "role": "ioc"}
    ]
    graph_edges = []
    for result in provider_results:
        provider = result.get("provider", "unknown")
        verdict = result.get("verdict", "no_data")
        graph_nodes.append({
            "id": provider,
            "label": provider,
            "verdict": verdict,
            "role": "provider",
        })
        graph_edges.append({"from": "ioc", "to": provider, "verdict": verdict})

    return render_template(
        "ioc_detail.html",
        ioc_value=ioc_value,
        ioc_type=ioc_type,
        provider_results=provider_results,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
    )
