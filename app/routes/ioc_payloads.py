"""IOC payload and template helpers shared by route surfaces."""

from app.pipeline.models import IOC, IOCType, append_ioc_by_type, group_by_type

from .analysis_modes import valid_analysis_modes_label


def _serialize_ioc(ioc: IOC) -> dict:
    """Serialize an IOC to a JSON-safe dict for history storage."""
    return {
        "type": ioc.type.value,
        "value": ioc.value,
        "raw_match": ioc.raw_match,
    }


def _group_iocs_for_template(iocs: list[IOC]) -> dict[IOCType, list[IOC]]:
    """Return template IOC groups through the shared route payload seam."""
    return group_by_type(iocs)


def _ioc_template_context(iocs: list[IOC]) -> dict[str, object]:
    """Return common result-template IOC context for fresh analysis routes."""
    total_count = len(iocs)
    no_results = total_count == 0
    return {
        "grouped": {} if no_results else _group_iocs_for_template(iocs),
        "total_count": total_count,
        "no_results": no_results,
    }


def _ioc_from_history_row(data: dict) -> IOC:
    return IOC(
        type=IOCType(data["type"]),
        value=data["value"],
        raw_match=data["raw_match"],
    )


def _append_history_ioc_row(grouped: dict[IOCType, list[IOC]], data: dict) -> None:
    append_ioc_by_type(grouped, _ioc_from_history_row(data))


def _group_history_iocs(raw_iocs: list[dict]) -> dict[IOCType, list[IOC]]:
    """Rebuild and group persisted IOC rows in one pass."""
    raw_count = len(raw_iocs)
    if raw_count == 0:
        return {}
    if raw_count == 1:
        ioc = _ioc_from_history_row(raw_iocs[0])
        return {ioc.type: [ioc]}
    if raw_count == 2:
        first = _ioc_from_history_row(raw_iocs[0])
        second = _ioc_from_history_row(raw_iocs[1])
        if first.type == second.type:
            return {first.type: [first, second]}
        return {first.type: [first], second.type: [second]}
    if raw_count == 3:
        first = _ioc_from_history_row(raw_iocs[0])
        second = _ioc_from_history_row(raw_iocs[1])
        third = _ioc_from_history_row(raw_iocs[2])
        if first.type == second.type == third.type:
            return {first.type: [first, second, third]}
        grouped: dict[IOCType, list[IOC]] = {}
        append_ioc_by_type(grouped, first)
        append_ioc_by_type(grouped, second)
        append_ioc_by_type(grouped, third)
        return grouped
    if raw_count == 4:
        first = _ioc_from_history_row(raw_iocs[0])
        second = _ioc_from_history_row(raw_iocs[1])
        third = _ioc_from_history_row(raw_iocs[2])
        fourth = _ioc_from_history_row(raw_iocs[3])
        if first.type == second.type == third.type == fourth.type:
            return {first.type: [first, second, third, fourth]}
        grouped: dict[IOCType, list[IOC]] = {}
        append_ioc_by_type(grouped, first)
        append_ioc_by_type(grouped, second)
        append_ioc_by_type(grouped, third)
        append_ioc_by_type(grouped, fourth)
        return grouped

    grouped: dict[IOCType, list[IOC]] = {}
    for data in raw_iocs:
        _append_history_ioc_row(grouped, data)
    return grouped


def _history_ioc_template_context(raw_iocs: list[dict], total_count: int) -> dict[str, object]:
    """Return common result-template IOC context for history replay routes."""
    no_results = total_count == 0
    return {
        "grouped": {} if no_results else _group_history_iocs(raw_iocs),
        "total_count": total_count,
        "no_results": no_results,
    }


def _serialize_iocs(iocs: list[IOC]) -> list[dict]:
    """Serialize IOC objects with direct accumulation for history storage."""
    ioc_count = len(iocs)
    if ioc_count == 0:
        return []
    if ioc_count == 1:
        return [_serialize_ioc(iocs[0])]
    if ioc_count == 2:
        return [_serialize_ioc(iocs[0]), _serialize_ioc(iocs[1])]
    if ioc_count == 3:
        return [_serialize_ioc(iocs[0]), _serialize_ioc(iocs[1]), _serialize_ioc(iocs[2])]
    if ioc_count == 4:
        return [
            _serialize_ioc(iocs[0]),
            _serialize_ioc(iocs[1]),
            _serialize_ioc(iocs[2]),
            _serialize_ioc(iocs[3]),
        ]

    serialized: list[dict] = []
    for ioc in iocs:
        _append_serialized_ioc(serialized, ioc)
    return serialized


def _append_serialized_ioc(serialized: list[dict], ioc: IOC) -> None:
    serialized.append(_serialize_ioc(ioc))


def _append_serialized_ioc_by_type(
    grouped: dict[str, list[dict]],
    type_key: str,
    serialized_ioc: dict,
) -> None:
    """Append serialized IOC payloads without setdefault's eager list allocation."""
    group = grouped.get(type_key)
    if group is None:
        group = []
        grouped[type_key] = group
    group.append(serialized_ioc)


def _append_serialized_ioc_payload(
    serialized_iocs: list[dict],
    grouped: dict[str, list[dict]],
    ioc: IOC,
) -> None:
    serialized = _serialize_ioc(ioc)
    serialized_iocs.append(serialized)
    _append_serialized_ioc_by_type(grouped, ioc.type.value, serialized)


def _serialized_ioc_response_payload(iocs: list[IOC]) -> tuple[list[dict], dict[str, list[dict]]]:
    """Return serialized IOC rows plus grouped rows for JSON API responses."""
    ioc_count = len(iocs)
    if ioc_count == 0:
        return [], {}
    if ioc_count == 1:
        ioc = iocs[0]
        serialized = _serialize_ioc(ioc)
        return [serialized], {ioc.type.value: [serialized]}
    if ioc_count == 2:
        first = iocs[0]
        second = iocs[1]
        first_serialized = _serialize_ioc(first)
        second_serialized = _serialize_ioc(second)
        serialized_iocs = [first_serialized, second_serialized]
        if first.type == second.type:
            return serialized_iocs, {first.type.value: serialized_iocs}
        return serialized_iocs, {
            first.type.value: [first_serialized],
            second.type.value: [second_serialized],
        }
    if ioc_count == 3:
        first = iocs[0]
        second = iocs[1]
        third = iocs[2]
        if first.type == second.type == third.type:
            serialized_iocs = [_serialize_ioc(first), _serialize_ioc(second), _serialize_ioc(third)]
            return serialized_iocs, {first.type.value: serialized_iocs}
        serialized_iocs: list[dict] = []
        grouped_summary: dict[str, list[dict]] = {}
        _append_serialized_ioc_payload(serialized_iocs, grouped_summary, first)
        _append_serialized_ioc_payload(serialized_iocs, grouped_summary, second)
        _append_serialized_ioc_payload(serialized_iocs, grouped_summary, third)
        return serialized_iocs, grouped_summary
    if ioc_count == 4:
        first = iocs[0]
        second = iocs[1]
        third = iocs[2]
        fourth = iocs[3]
        if first.type == second.type == third.type == fourth.type:
            serialized_iocs = [
                _serialize_ioc(first),
                _serialize_ioc(second),
                _serialize_ioc(third),
                _serialize_ioc(fourth),
            ]
            return serialized_iocs, {first.type.value: serialized_iocs}
        serialized_iocs: list[dict] = []
        grouped_summary: dict[str, list[dict]] = {}
        _append_serialized_ioc_payload(serialized_iocs, grouped_summary, first)
        _append_serialized_ioc_payload(serialized_iocs, grouped_summary, second)
        _append_serialized_ioc_payload(serialized_iocs, grouped_summary, third)
        _append_serialized_ioc_payload(serialized_iocs, grouped_summary, fourth)
        return serialized_iocs, grouped_summary

    serialized_iocs: list[dict] = []
    grouped_summary: dict[str, list[dict]] = {}
    for ioc in iocs:
        _append_serialized_ioc_payload(serialized_iocs, grouped_summary, ioc)
    return serialized_iocs, grouped_summary


def api_analysis_response_payload(
    iocs: list[IOC],
    *,
    mode: str,
    job_id: str | None = None,
) -> dict[str, object]:
    """Return the public API analyze response payload."""
    total_count = len(iocs)
    if total_count == 0:
        return {
            "mode": mode,
            "total_count": 0,
            "iocs": [],
            "grouped": {},
        }

    serialized_iocs, grouped_summary = _serialized_ioc_response_payload(iocs)
    response: dict[str, object] = {
        "mode": mode,
        "total_count": total_count,
        "iocs": serialized_iocs,
        "grouped": grouped_summary,
    }
    if job_id is not None:
        response["job_id"] = job_id
        response["status_url"] = f"/api/status/{job_id}"
    return response


def api_json_required_error_payload() -> dict[str, str]:
    """Return the API error for missing or invalid JSON bodies."""
    return {"error": "Request body must be JSON"}


def api_text_required_error_payload() -> dict[str, str]:
    """Return the API error for missing, invalid, or empty text."""
    return {"error": "Field 'text' is required and must be non-empty"}


def api_invalid_mode_error_payload(mode: object) -> dict[str, str]:
    """Return the API error for unsupported analysis modes."""
    return {"error": f"Invalid mode '{mode}'. Must be {valid_analysis_modes_label()}."}


def api_no_provider_error_payload() -> dict[str, str]:
    """Return the API error for Online mode without configured providers."""
    return {
        "error": (
            "No provider API keys configured. "
            "Configure at least one provider in /settings."
        ),
    }
