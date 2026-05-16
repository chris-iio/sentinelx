"""IOC detail page route."""

from flask import abort, current_app, render_template

from app import limiter
from app.pipeline.models import IOC_TYPE_VALUES

from . import bp


_VALID_IOC_TYPES = frozenset(IOC_TYPE_VALUES)
_GRAPH_IOC_ID = "ioc"
_UNKNOWN_PROVIDER = "unknown"
_DEFAULT_VERDICT = "no_data"


def _provider_graph_data(
    provider_results: list[dict],
    ioc_value: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    result_count = len(provider_results)
    if result_count == 0:
        return [], []

    ioc_node = {"id": _GRAPH_IOC_ID, "label": ioc_value, "verdict": _GRAPH_IOC_ID, "role": "ioc"}
    if result_count == 1:
        result = provider_results[0]
        provider = result.get("provider", _UNKNOWN_PROVIDER)
        verdict = result.get("verdict", _DEFAULT_VERDICT)
        return [
            ioc_node,
            {
                "id": provider,
                "label": provider,
                "verdict": verdict,
                "role": "provider",
            },
        ], [{"from": _GRAPH_IOC_ID, "to": provider, "verdict": verdict}]
    if result_count == 2:
        first = provider_results[0]
        first_provider = first.get("provider", _UNKNOWN_PROVIDER)
        first_verdict = first.get("verdict", _DEFAULT_VERDICT)
        second = provider_results[1]
        second_provider = second.get("provider", _UNKNOWN_PROVIDER)
        second_verdict = second.get("verdict", _DEFAULT_VERDICT)
        return [
            ioc_node,
            {
                "id": first_provider,
                "label": first_provider,
                "verdict": first_verdict,
                "role": "provider",
            },
            {
                "id": second_provider,
                "label": second_provider,
                "verdict": second_verdict,
                "role": "provider",
            },
        ], [
            {"from": _GRAPH_IOC_ID, "to": first_provider, "verdict": first_verdict},
            {"from": _GRAPH_IOC_ID, "to": second_provider, "verdict": second_verdict},
        ]
    if result_count == 3:
        first = provider_results[0]
        first_provider = first.get("provider", _UNKNOWN_PROVIDER)
        first_verdict = first.get("verdict", _DEFAULT_VERDICT)
        second = provider_results[1]
        second_provider = second.get("provider", _UNKNOWN_PROVIDER)
        second_verdict = second.get("verdict", _DEFAULT_VERDICT)
        third = provider_results[2]
        third_provider = third.get("provider", _UNKNOWN_PROVIDER)
        third_verdict = third.get("verdict", _DEFAULT_VERDICT)
        return [
            ioc_node,
            {
                "id": first_provider,
                "label": first_provider,
                "verdict": first_verdict,
                "role": "provider",
            },
            {
                "id": second_provider,
                "label": second_provider,
                "verdict": second_verdict,
                "role": "provider",
            },
            {
                "id": third_provider,
                "label": third_provider,
                "verdict": third_verdict,
                "role": "provider",
            },
        ], [
            {"from": _GRAPH_IOC_ID, "to": first_provider, "verdict": first_verdict},
            {"from": _GRAPH_IOC_ID, "to": second_provider, "verdict": second_verdict},
            {"from": _GRAPH_IOC_ID, "to": third_provider, "verdict": third_verdict},
        ]

    graph_nodes: list[dict[str, str]] = [ioc_node]
    graph_edges: list[dict[str, str]] = []
    for result in provider_results:
        provider = result.get("provider", _UNKNOWN_PROVIDER)
        verdict = result.get("verdict", _DEFAULT_VERDICT)
        graph_nodes.append({
            "id": provider,
            "label": provider,
            "verdict": verdict,
            "role": "provider",
        })
        graph_edges.append({"from": _GRAPH_IOC_ID, "to": provider, "verdict": verdict})
    return graph_nodes, graph_edges


@bp.route("/ioc/<ioc_type>/<path:ioc_value>")
@limiter.limit("30 per minute")
def ioc_detail(ioc_type: str, ioc_value: str) -> str:
    """IOC detail page — shows all cached provider results for a single IOC."""
    if ioc_type not in _VALID_IOC_TYPES:
        abort(404)

    cache = current_app.cache_store
    provider_results = cache.get_all_for_ioc(ioc_value, ioc_type)

    graph_nodes, graph_edges = _provider_graph_data(provider_results, ioc_value)

    return render_template(
        "ioc_detail.html",
        ioc_value=ioc_value,
        ioc_type=ioc_type,
        provider_results=provider_results,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
    )
