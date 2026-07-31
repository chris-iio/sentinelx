"""IOC detail relationship graph payload helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.pipeline.models import IOC_TYPE_VALUES

from .template_results import TemplateResult, apply_template_result

_GRAPH_IOC_ID = "ioc"
_UNKNOWN_PROVIDER = "unknown"
_DEFAULT_VERDICT = "no_data"
VALID_IOC_TYPES = frozenset(IOC_TYPE_VALUES)


def _provider_graph_payload(result: dict) -> tuple[dict[str, str], dict[str, str]]:
    provider = result.get("provider", _UNKNOWN_PROVIDER)
    verdict = result.get("verdict", _DEFAULT_VERDICT)
    return {
        "id": provider,
        "label": provider,
        "verdict": verdict,
        "role": "provider",
    }, {"from": _GRAPH_IOC_ID, "to": provider, "verdict": verdict}


def _append_provider_graph_payload(
    graph_nodes: list[dict[str, str]],
    graph_edges: list[dict[str, str]],
    result: dict,
) -> None:
    node, edge = _provider_graph_payload(result)
    graph_nodes.append(node)
    graph_edges.append(edge)


def provider_graph_data(
    provider_results: list[dict],
    ioc_value: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return IOC/provider graph nodes and edges for the detail page."""
    result_count = len(provider_results)
    if result_count == 0:
        return [], []

    ioc_node = {"id": _GRAPH_IOC_ID, "label": ioc_value, "verdict": _GRAPH_IOC_ID, "role": "ioc"}
    if result_count == 1:
        first_node, first_edge = _provider_graph_payload(provider_results[0])
        return [ioc_node, first_node], [first_edge]
    if result_count == 2:
        first_node, first_edge = _provider_graph_payload(provider_results[0])
        second_node, second_edge = _provider_graph_payload(provider_results[1])
        return [ioc_node, first_node, second_node], [first_edge, second_edge]
    if result_count == 3:
        first_node, first_edge = _provider_graph_payload(provider_results[0])
        second_node, second_edge = _provider_graph_payload(provider_results[1])
        third_node, third_edge = _provider_graph_payload(provider_results[2])
        return [
            ioc_node,
            first_node,
            second_node,
            third_node,
        ], [first_edge, second_edge, third_edge]
    if result_count == 4:
        first_node, first_edge = _provider_graph_payload(provider_results[0])
        second_node, second_edge = _provider_graph_payload(provider_results[1])
        third_node, third_edge = _provider_graph_payload(provider_results[2])
        fourth_node, fourth_edge = _provider_graph_payload(provider_results[3])
        return [
            ioc_node,
            first_node,
            second_node,
            third_node,
            fourth_node,
        ], [first_edge, second_edge, third_edge, fourth_edge]

    graph_nodes: list[dict[str, str]] = [ioc_node]
    graph_edges: list[dict[str, str]] = []
    for result in provider_results:
        _append_provider_graph_payload(graph_nodes, graph_edges, result)
    return graph_nodes, graph_edges


def detail_template_context(
    *,
    ioc_value: str,
    ioc_type: str,
    provider_results: list[dict],
) -> dict[str, object]:
    """Return template context for the IOC detail page."""
    graph_nodes, graph_edges = provider_graph_data(provider_results, ioc_value)
    return {
        "ioc_value": ioc_value,
        "ioc_type": ioc_type,
        "provider_results": provider_results,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
    }


def load_detail_template_context(
    cache_store: object,
    *,
    ioc_type: str,
    ioc_value: str,
) -> dict[str, object] | None:
    """Return IOC detail context, or None when the IOC type is unsupported."""
    if ioc_type not in VALID_IOC_TYPES:
        return None
    provider_results = cache_store.get_all_for_ioc(ioc_value, ioc_type)  # type: ignore[attr-defined]
    return detail_template_context(
        ioc_value=ioc_value,
        ioc_type=ioc_type,
        provider_results=provider_results,
    )


def detail_page_result(
    cache_store: object,
    *,
    ioc_type: str,
    ioc_value: str,
) -> TemplateResult:
    """Return the IOC detail page render decision for a requested IOC."""
    context = load_detail_template_context(
        cache_store,
        ioc_type=ioc_type,
        ioc_value=ioc_value,
    )
    if context is None:
        return TemplateResult(None, None, 404)
    return TemplateResult("ioc_detail.html", context, 200)


def detail_page_route_response(
    cache_store: object,
    *,
    ioc_type: str,
    ioc_value: str,
    abort_request: Callable[[int], Any],
    render_template: Callable[..., Any],
) -> Any:
    """Apply the IOC detail render-or-404 decision for route-supplied dependencies."""
    return apply_template_result(
        detail_page_result(
            cache_store,
            ioc_type=ioc_type,
            ioc_value=ioc_value,
        ),
        abort_request=abort_request,
        render_template=render_template,
    )
