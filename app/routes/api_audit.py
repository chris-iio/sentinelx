"""Validated local REST API for the audit workbench."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from flask import Blueprint, Response, current_app, jsonify, request

from app import limiter
from app.audit import runner
from app.audit.parse import parse_intake
from app.audit.poc import poc_template
from app.audit.report import engagement_report
from app.audit.store import (
    ENGAGEMENT_STATUSES,
    FINDING_STATUSES,
    PLATFORMS,
    SEVERITIES,
)

bp_api_audit = Blueprint("api_audit", __name__, url_prefix="/api/audit")

MAX_REQUEST_BYTES = 512 * 1024
MAX_INTAKE_CHARS = 256 * 1024
MAX_IMPORT_FINDINGS = 200
MAX_SAVED_RUNS = 128
SAVED_RUN_TTL_S = 60 * 60

_ENGAGEMENT_LIMITS = {
    "name": 200,
    "platform": 32,
    "url": 2048,
    "scope": 100_000,
    "prize_pool": 100,
    "deadline": 64,
}
_FINDING_LIMITS = {
    "title": 200,
    "severity": 32,
    "status": 32,
    "target": 1024,
    "description": 256_000,
    "impact": 256_000,
    "poc": 256_000,
    "remediation": 256_000,
}


class _ValidationError(ValueError):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


@bp_api_audit.errorhandler(_ValidationError)
def _validation_error(exc: _ValidationError):
    return _error(str(exc), exc.status)


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _json_body() -> dict:
    if request.content_length is not None and request.content_length > MAX_REQUEST_BYTES:
        raise _ValidationError(
            f"Request body exceeds {MAX_REQUEST_BYTES} bytes.", status=413
        )
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise _ValidationError("Request body must be a JSON object.")
    return body


def _reject_unknown(body: dict, allowed: set[str]) -> None:
    unknown = sorted(set(body) - allowed)
    if unknown:
        raise _ValidationError(f"Unknown field: {unknown[0]}.")


def _text(
    body: dict,
    field: str,
    max_chars: int,
    *,
    default: str | None = None,
    strip: bool = False,
) -> str | None:
    if field not in body:
        return default
    value = body[field]
    if not isinstance(value, str):
        raise _ValidationError(f"Field '{field}' must be a string.")
    if len(value) > max_chars:
        raise _ValidationError(f"Field '{field}' exceeds {max_chars} characters.")
    return value.strip() if strip else value


def _boolean(body: dict, field: str, *, default: bool = False) -> bool:
    if field not in body:
        return default
    value = body[field]
    if not isinstance(value, bool):
        raise _ValidationError(f"Field '{field}' must be a boolean.")
    return value


def _validate_id(value: str, label: str) -> None:
    if len(value) > 64:
        raise _ValidationError(f"{label} id is too long.")


def _finding_fields(body: dict, *, partial: bool = False) -> dict[str, str]:
    _reject_unknown(body, set(_FINDING_LIMITS))
    fields: dict[str, str] = {}
    defaults = {
        "title": "",
        "severity": "info",
        "status": "draft",
        "target": "",
        "description": "",
        "impact": "",
        "poc": "",
        "remediation": "",
    }
    for field, limit in _FINDING_LIMITS.items():
        if partial and field not in body:
            continue
        value = _text(
            body,
            field,
            limit,
            default=defaults[field],
            strip=field in {"title", "severity", "status", "target"},
        )
        fields[field] = cast(str, value)
    if "title" in fields and not fields["title"]:
        raise _ValidationError("Field 'title' is required.")
    if "severity" in fields and fields["severity"] not in SEVERITIES:
        raise _ValidationError(f"severity must be one of: {', '.join(SEVERITIES)}.")
    if "status" in fields and fields["status"] not in FINDING_STATUSES:
        raise _ValidationError(f"status must be one of: {', '.join(FINDING_STATUSES)}.")
    if partial and not fields:
        raise _ValidationError("At least one editable finding field is required.")
    return fields


@dataclass(frozen=True)
class _SavedRun:
    engagement_id: str
    result: runner.RunResult
    candidates_json: str
    saved_at: float
    imported: bool = False


_SAVED_RUNS: OrderedDict[str, _SavedRun] = OrderedDict()
_SAVED_RUNS_LOCK = threading.Lock()


def _prune_runs(now: float) -> None:
    expired = [
        run_id
        for run_id, saved in _SAVED_RUNS.items()
        if now - saved.saved_at > SAVED_RUN_TTL_S
    ]
    for run_id in expired:
        _SAVED_RUNS.pop(run_id, None)
    while len(_SAVED_RUNS) >= MAX_SAVED_RUNS:
        _SAVED_RUNS.popitem(last=False)


def _save_run(engagement_id: str, result: runner.RunResult, candidates: list[dict]) -> None:
    saved = _SavedRun(
        engagement_id=engagement_id,
        result=result,
        candidates_json=json.dumps(candidates, ensure_ascii=False, separators=(",", ":")),
        saved_at=time.monotonic(),
    )
    with _SAVED_RUNS_LOCK:
        _prune_runs(saved.saved_at)
        _SAVED_RUNS[result.run_id] = saved


def _consume_run(engagement_id: str, run_id: str) -> _SavedRun:
    now = time.monotonic()
    with _SAVED_RUNS_LOCK:
        _prune_runs(now)
        saved = _SAVED_RUNS.get(run_id)
        if saved is None or saved.engagement_id != engagement_id:
            raise _ValidationError("Saved run not found or expired.", status=404)
        if saved.imported:
            raise _ValidationError("Saved run was already imported.", status=409)
        _SAVED_RUNS[run_id] = replace(saved, imported=True)
        return saved


def _run_payload(
    result: runner.RunResult,
    candidates: list[dict],
    *,
    created: int = 0,
    imported: bool = False,
) -> dict:
    if result.timed_out:
        exit_status = "timed_out"
    elif result.exit_code == -1 and result.error:
        exit_status = "spawn_error"
    else:
        exit_status = "exited"
    return {
        "run_id": result.run_id,
        "tool": Path(result.argv[0]).name,
        "profile": result.profile,
        "argv": list(result.argv),
        "root": result.root,
        "target": result.target,
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "exit_status": exit_status,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "truncated": result.truncated,
        "output": result.output,
        "output_sha256": hashlib.sha256(result.output.encode("utf-8")).hexdigest(),
        "error": result.error,
        "candidates": candidates,
        "created": created,
        "imported": imported,
    }


def _create_candidates(
    engagement_id: str,
    candidates: list[dict],
    *,
    allow_freeform: bool = False,
) -> list[dict]:
    importable = (
        candidates
        if allow_freeform
        else [c for c in candidates if c.get("source") != "freeform"]
    )
    if len(importable) > MAX_IMPORT_FINDINGS:
        raise _ValidationError(
            f"Import exceeds {MAX_IMPORT_FINDINGS} findings.", status=422
        )
    created = []
    for candidate in importable:
        finding_id = current_app.audit_store.create_finding(
            engagement_id,
            title=candidate["title"],
            severity=candidate["severity"],
            target=candidate.get("target", ""),
            description=candidate.get("description", ""),
        )
        if finding_id is not None:
            created.append(current_app.audit_store.get_finding(finding_id))
    return created


@bp_api_audit.route("/meta", methods=["GET"])
@limiter.limit("120 per minute")
def audit_meta():
    return jsonify(
        {
            "platforms": list(PLATFORMS),
            "severities": list(SEVERITIES),
            "engagement_statuses": list(ENGAGEMENT_STATUSES),
            "finding_statuses": list(FINDING_STATUSES),
        }
    )


@bp_api_audit.route("/engagements", methods=["GET"])
@limiter.limit("120 per minute")
def list_engagements():
    return jsonify({"engagements": current_app.audit_store.list_engagements()})


@bp_api_audit.route("/engagements", methods=["POST"])
@limiter.limit("30 per minute")
def create_engagement():
    body = _json_body()
    _reject_unknown(body, set(_ENGAGEMENT_LIMITS))
    name = _text(body, "name", _ENGAGEMENT_LIMITS["name"], default="", strip=True)
    if not name:
        raise _ValidationError("Field 'name' is required.")
    platform = cast(str, _text(body, "platform", 32, default="other", strip=True))
    if platform not in PLATFORMS:
        raise _ValidationError(f"platform must be one of: {', '.join(PLATFORMS)}.")
    values = {
        field: _text(
            body,
            field,
            limit,
            default="",
            strip=field != "scope",
        )
        for field, limit in _ENGAGEMENT_LIMITS.items()
        if field not in {"name", "platform"}
    }
    engagement_id = current_app.audit_store.create_engagement(
        name=name, platform=platform, **values
    )
    return jsonify({"engagement": current_app.audit_store.get_engagement(engagement_id)}), 201


@bp_api_audit.route("/engagements/<engagement_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_engagement(engagement_id: str):
    _validate_id(engagement_id, "Engagement")
    engagement = current_app.audit_store.get_engagement(engagement_id)
    if engagement is None:
        return _error("Engagement not found.", 404)
    engagement["stats"] = current_app.audit_store.engagement_stats(engagement_id)
    return jsonify({"engagement": engagement})


@bp_api_audit.route("/engagements/<engagement_id>", methods=["PATCH"])
@limiter.limit("60 per minute")
def update_engagement(engagement_id: str):
    _validate_id(engagement_id, "Engagement")
    body = _json_body()
    _reject_unknown(body, {"status"})
    status = _text(body, "status", 32, strip=True)
    if status not in ENGAGEMENT_STATUSES:
        raise _ValidationError(
            f"Field 'status' must be one of: {', '.join(ENGAGEMENT_STATUSES)}."
        )
    if not current_app.audit_store.set_engagement_status(engagement_id, status):
        return _error("Engagement not found.", 404)
    return jsonify({"engagement": current_app.audit_store.get_engagement(engagement_id)})


@bp_api_audit.route("/engagements/<engagement_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
def delete_engagement(engagement_id: str):
    _validate_id(engagement_id, "Engagement")
    if not current_app.audit_store.delete_engagement(engagement_id):
        return _error("Engagement not found.", 404)
    return jsonify({"deleted": True})


@bp_api_audit.route("/engagements/<engagement_id>/findings", methods=["GET"])
@limiter.limit("120 per minute")
def list_findings(engagement_id: str):
    _validate_id(engagement_id, "Engagement")
    if current_app.audit_store.get_engagement(engagement_id) is None:
        return _error("Engagement not found.", 404)
    severity = request.args.get("severity")
    status = request.args.get("status")
    if severity is not None and severity not in SEVERITIES:
        raise _ValidationError(f"severity must be one of: {', '.join(SEVERITIES)}.")
    if status is not None and status not in FINDING_STATUSES:
        raise _ValidationError(f"status must be one of: {', '.join(FINDING_STATUSES)}.")
    findings = current_app.audit_store.list_findings(
        engagement_id, severity=severity, status=status
    )
    return jsonify(
        {
            "findings": findings,
            "stats": current_app.audit_store.engagement_stats(engagement_id),
        }
    )


@bp_api_audit.route("/engagements/<engagement_id>/findings", methods=["POST"])
@limiter.limit("60 per minute")
def create_finding(engagement_id: str):
    _validate_id(engagement_id, "Engagement")
    fields = _finding_fields(_json_body())
    finding_id = current_app.audit_store.create_finding(engagement_id, **fields)
    if finding_id is None:
        return _error("Engagement not found.", 404)
    return jsonify({"finding": current_app.audit_store.get_finding(finding_id)}), 201


@bp_api_audit.route("/engagements/<engagement_id>/intake", methods=["POST"])
@limiter.limit("20 per minute")
def intake(engagement_id: str):
    _validate_id(engagement_id, "Engagement")
    if current_app.audit_store.get_engagement(engagement_id) is None:
        return _error("Engagement not found.", 404)
    body = _json_body()
    _reject_unknown(body, {"text", "create"})
    text = _text(body, "text", MAX_INTAKE_CHARS, default="")
    if not text or not text.strip():
        raise _ValidationError("Field 'text' is required.")
    create = _boolean(body, "create")
    candidates = parse_intake(text)
    if not create:
        return jsonify({"candidates": candidates, "created": 0})
    created = _create_candidates(engagement_id, candidates, allow_freeform=True)
    return jsonify(
        {"candidates": candidates, "created": len(created), "findings": created}
    ), 201


@bp_api_audit.route("/engagements/<engagement_id>/report.md", methods=["GET"])
@limiter.limit("30 per minute")
def report(engagement_id: str):
    _validate_id(engagement_id, "Engagement")
    engagement = current_app.audit_store.get_engagement(engagement_id)
    if engagement is None:
        return _error("Engagement not found.", 404)
    findings = current_app.audit_store.list_findings(engagement_id)
    markdown = engagement_report(
        engagement, findings, current_app.audit_store.engagement_stats(engagement_id)
    )
    return Response(
        markdown,
        mimetype="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="report-{engagement_id[:8]}.md"'
        },
    )


@bp_api_audit.route("/findings/<finding_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_finding(finding_id: str):
    _validate_id(finding_id, "Finding")
    finding = current_app.audit_store.get_finding(finding_id)
    if finding is None:
        return _error("Finding not found.", 404)
    return jsonify({"finding": finding})


@bp_api_audit.route("/tools", methods=["GET"])
@limiter.limit("120 per minute")
def list_tools():
    profiles = runner.available_profiles()
    roots = runner.workspace_roots()
    return jsonify(
        {
            "tools": [
                {
                    "name": name,
                    "summary": profile["summary"],
                    "target": profile["target"],
                    "needs_wordlist": profile["needs_wordlist"],
                    "format": profile["format"],
                    "installed": profile["installed"],
                }
                for name, profile in profiles.items()
            ],
            "workspace_roots": [str(root) for root in roots],
            "execution_enabled": bool(roots),
        }
    )


@bp_api_audit.route("/engagements/<engagement_id>/run", methods=["POST"])
@limiter.limit("6 per minute")
def run_tool(engagement_id: str):
    """Execute a tool once and save its immutable output for later import."""
    _validate_id(engagement_id, "Engagement")
    if current_app.audit_store.get_engagement(engagement_id) is None:
        return _error("Engagement not found.", 404)
    body = _json_body()
    _reject_unknown(body, {"profile", "target", "wordlist"})
    profile = _text(body, "profile", 64, default="", strip=True)
    if not profile:
        raise _ValidationError("Field 'profile' is required.")
    target = cast(str, _text(body, "target", 1024, default=""))
    wordlist = cast(str, _text(body, "wordlist", 1024, default=""))
    try:
        result = runner.run_profile(profile, target=target, wordlist=wordlist)
    except runner.RunCapacityError as exc:
        return _error(str(exc), 429)
    except ValueError as exc:
        return _error(str(exc), 400)

    candidates = parse_intake(result.output) if result.output else []
    _save_run(engagement_id, result, candidates)
    return jsonify(_run_payload(result, candidates))


@bp_api_audit.route(
    "/engagements/<engagement_id>/runs/<run_id>/import", methods=["POST"]
)
@limiter.limit("20 per minute")
def import_tool_run(engagement_id: str, run_id: str):
    """Import candidates from the exact saved output without another execution."""
    _validate_id(engagement_id, "Engagement")
    _validate_id(run_id, "Run")
    if current_app.audit_store.get_engagement(engagement_id) is None:
        return _error("Engagement not found.", 404)
    body = _json_body()
    _reject_unknown(body, set())
    saved = _consume_run(engagement_id, run_id)
    candidates = json.loads(saved.candidates_json)
    created = _create_candidates(engagement_id, candidates)
    return jsonify(
        _run_payload(saved.result, candidates, created=len(created), imported=True)
    ), 201


@bp_api_audit.route("/findings/<finding_id>/poc.sol", methods=["GET"])
@limiter.limit("30 per minute")
def finding_poc(finding_id: str):
    _validate_id(finding_id, "Finding")
    finding = current_app.audit_store.get_finding(finding_id)
    if finding is None:
        return _error("Finding not found.", 404)
    engagement = current_app.audit_store.get_engagement(finding["engagement_id"])
    source = poc_template(finding, engagement)
    return Response(
        source,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="poc-{finding_id[:8]}.t.sol"'
        },
    )


@bp_api_audit.route("/findings/<finding_id>", methods=["PATCH"])
@limiter.limit("60 per minute")
def update_finding(finding_id: str):
    _validate_id(finding_id, "Finding")
    fields = _finding_fields(_json_body(), partial=True)
    if not current_app.audit_store.update_finding(finding_id, fields):
        return _error("Finding not found.", 404)
    return jsonify({"finding": current_app.audit_store.get_finding(finding_id)})


@bp_api_audit.route("/findings/<finding_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
def delete_finding(finding_id: str):
    _validate_id(finding_id, "Finding")
    if not current_app.audit_store.delete_finding(finding_id):
        return _error("Finding not found.", 404)
    return jsonify({"deleted": True})
