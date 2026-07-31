"""Server-rendered routes for the local Audit workspace."""
from __future__ import annotations

import json
import re

from flask import (
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app import limiter
from app.audit import runner
from app.audit.parse import parse_intake
from app.audit.report import engagement_report
from app.audit.store import (
    ENGAGEMENT_STATUSES,
    FINDING_STATUSES,
    PLATFORMS,
    SEVERITIES,
)

from . import bp
from .api_audit import _consume_run, _create_candidates, _save_run

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
    "target": 1024,
    "description": 256_000,
    "impact": 256_000,
    "poc": 256_000,
    "remediation": 256_000,
}
_MAX_INTAKE_CHARS = 256 * 1024
_MAX_IMPORT_FINDINGS = 200
_ID_RE = re.compile(r"[a-f0-9]{32}")


class _FormError(ValueError):
    """A safe validation message for a server-rendered form."""


def _form_text(field: str, max_chars: int, *, strip: bool = False) -> str:
    value = request.form.get(field, "")
    if len(value) > max_chars:
        raise _FormError(f"{field.replace('_', ' ').capitalize()} is too long.")
    return value.strip() if strip else value


def _entity_id_or_404(value: str) -> str:
    if not _ID_RE.fullmatch(value):
        abort(404)
    return value


def _engagement_or_404(engagement_id: str) -> dict:
    engagement = current_app.audit_store.get_engagement(
        _entity_id_or_404(engagement_id)
    )
    if engagement is None:
        abort(404)
    return engagement


def _finding_or_404(finding_id: str) -> dict:
    finding = current_app.audit_store.get_finding(_entity_id_or_404(finding_id))
    if finding is None:
        abort(404)
    return finding


def _engagement_url(engagement_id: str) -> str:
    return url_for("main.audit_engagement_detail", engagement_id=engagement_id)


def _render_engagement(engagement_id: str, **preview: object):
    engagement = _engagement_or_404(engagement_id)
    return render_template(
        "audit_engagement.html",
        engagement=engagement,
        findings=current_app.audit_store.list_findings(engagement_id),
        stats=current_app.audit_store.engagement_stats(engagement_id),
        engagement_statuses=ENGAGEMENT_STATUSES,
        severities=SEVERITIES,
        profiles=runner.available_profiles(),
        workspace_roots=runner.workspace_roots(),
        **preview,
    )


def _finding_fields() -> dict[str, str]:
    values = {
        field: _form_text(
            field,
            limit,
            strip=field in {"title", "severity", "target"},
        )
        for field, limit in _FINDING_LIMITS.items()
    }
    if not values["title"]:
        raise _FormError("Finding title is required.")
    if values["severity"] not in SEVERITIES:
        raise _FormError("Select a valid severity.")
    return values


def _create_intake_findings(engagement_id: str, candidates: list[dict]) -> int:
    if len(candidates) > _MAX_IMPORT_FINDINGS:
        raise _FormError(
            f"Preview has more than {_MAX_IMPORT_FINDINGS} findings. Narrow the input."
        )
    created = 0
    for candidate in candidates:
        finding_id = current_app.audit_store.create_finding(
            engagement_id,
            title=candidate["title"],
            severity=candidate["severity"],
            target=candidate.get("target", ""),
            description=candidate.get("description", ""),
        )
        if finding_id is not None:
            created += 1
    return created


@bp.route("/audit")
@limiter.limit("60 per minute")
def audit_engagements_list():
    """List engagements and show the create form."""
    return render_template(
        "audit_engagements.html",
        engagements=current_app.audit_store.list_engagements(),
        platforms=PLATFORMS,
    )


@bp.route("/audit/engagements", methods=["POST"])
@limiter.limit("20 per minute")
def audit_engagement_create():
    """Create one validated engagement with the owning AuditStore."""
    try:
        values = {
            field: _form_text(
                field,
                limit,
                strip=field != "scope",
            )
            for field, limit in _ENGAGEMENT_LIMITS.items()
        }
        if not values["name"]:
            raise _FormError("Engagement name is required.")
        if values["platform"] not in PLATFORMS:
            raise _FormError("Select a valid platform.")
        if values["url"] and not values["url"].startswith(("http://", "https://")):
            raise _FormError("Engagement URL must start with http:// or https://.")
    except _FormError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.audit_engagements_list"))

    engagement_id = current_app.audit_store.create_engagement(**values)
    flash("Engagement created.", "info")
    return redirect(_engagement_url(engagement_id))


@bp.route("/audit/engagements/<engagement_id>")
@limiter.limit("60 per minute")
def audit_engagement_detail(engagement_id: str):
    """Show one engagement, its findings, intake, and reproducible tools."""
    return _render_engagement(engagement_id)


@bp.route("/audit/engagements/<engagement_id>/status", methods=["POST"])
@limiter.limit("20 per minute")
def audit_engagement_status(engagement_id: str):
    """Set the analyst-managed engagement status."""
    engagement = _engagement_or_404(engagement_id)
    try:
        status = _form_text("status", 32, strip=True)
        if status not in ENGAGEMENT_STATUSES:
            raise _FormError("Select a valid engagement status.")
    except _FormError as exc:
        flash(str(exc), "error")
        return redirect(_engagement_url(engagement["id"]))
    current_app.audit_store.set_engagement_status(engagement["id"], status)
    return redirect(_engagement_url(engagement["id"]))


@bp.route("/audit/engagements/<engagement_id>/delete", methods=["POST"])
@limiter.limit("10 per minute")
def audit_engagement_delete(engagement_id: str):
    """Delete one engagement and its findings."""
    engagement = _engagement_or_404(engagement_id)
    current_app.audit_store.delete_engagement(engagement["id"])
    flash("Engagement deleted.", "info")
    return redirect(url_for("main.audit_engagements_list"))


@bp.route("/audit/engagements/<engagement_id>/findings", methods=["POST"])
@limiter.limit("30 per minute")
def audit_finding_create(engagement_id: str):
    """Create a draft finding under an engagement."""
    engagement = _engagement_or_404(engagement_id)
    try:
        fields = _finding_fields()
    except _FormError as exc:
        flash(str(exc), "error")
        return redirect(_engagement_url(engagement["id"]))
    finding_id = current_app.audit_store.create_finding(engagement["id"], **fields)
    if finding_id is None:
        abort(404)
    flash("Draft finding created. Add evidence and a reproducible check.", "info")
    return redirect(url_for("main.audit_finding_detail", finding_id=finding_id))


@bp.route("/audit/findings/<finding_id>")
@limiter.limit("60 per minute")
def audit_finding_detail(finding_id: str):
    """Show the finding editor and analyst disposition controls."""
    finding = _finding_or_404(finding_id)
    engagement = current_app.audit_store.get_engagement(finding["engagement_id"])
    if engagement is None:
        abort(404)
    return render_template(
        "audit_finding.html",
        finding=finding,
        engagement=engagement,
        severities=SEVERITIES,
        finding_statuses=FINDING_STATUSES,
    )


@bp.route("/audit/findings/<finding_id>/edit", methods=["POST"])
@limiter.limit("30 per minute")
def audit_finding_edit(finding_id: str):
    """Update claim, evidence, reproducible check, and remediation fields."""
    finding = _finding_or_404(finding_id)
    try:
        fields = _finding_fields()
    except _FormError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.audit_finding_detail", finding_id=finding["id"]))
    current_app.audit_store.update_finding(finding["id"], fields)
    flash("Finding evidence updated.", "info")
    return redirect(url_for("main.audit_finding_detail", finding_id=finding["id"]))


@bp.route("/audit/findings/<finding_id>/status", methods=["POST"])
@limiter.limit("30 per minute")
def audit_finding_status(finding_id: str):
    """Record the analyst's finding disposition/status."""
    finding = _finding_or_404(finding_id)
    try:
        status = _form_text("status", 32, strip=True)
        if status not in FINDING_STATUSES:
            raise _FormError("Select a valid finding status.")
    except _FormError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.audit_finding_detail", finding_id=finding["id"]))
    current_app.audit_store.update_finding(finding["id"], {"status": status})
    return redirect(url_for("main.audit_finding_detail", finding_id=finding["id"]))


@bp.route("/audit/findings/<finding_id>/delete", methods=["POST"])
@limiter.limit("10 per minute")
def audit_finding_delete(finding_id: str):
    """Delete one finding and return to its engagement."""
    finding = _finding_or_404(finding_id)
    current_app.audit_store.delete_finding(finding["id"])
    flash("Finding deleted.", "info")
    return redirect(_engagement_url(finding["engagement_id"]))


@bp.route("/audit/engagements/<engagement_id>/intake/preview", methods=["POST"])
@limiter.limit("20 per minute")
def audit_intake_preview(engagement_id: str):
    """Parse scanner output without changing analyst-owned findings."""
    engagement = _engagement_or_404(engagement_id)
    try:
        text = _form_text("text", _MAX_INTAKE_CHARS)
        if not text.strip():
            raise _FormError("Scanner output is required.")
        candidates = parse_intake(text)
        if len(candidates) > _MAX_IMPORT_FINDINGS:
            raise _FormError(
                f"Preview has more than {_MAX_IMPORT_FINDINGS} findings. Narrow the input."
            )
    except _FormError as exc:
        flash(str(exc), "error")
        return redirect(_engagement_url(engagement["id"]))
    return _render_engagement(
        engagement["id"], intake_preview=candidates, intake_text=text
    )


@bp.route("/audit/engagements/<engagement_id>/intake/import", methods=["POST"])
@limiter.limit("20 per minute")
def audit_intake_import(engagement_id: str):
    """Import a fresh parse of the previewed scanner output as draft claims."""
    engagement = _engagement_or_404(engagement_id)
    try:
        text = _form_text("text", _MAX_INTAKE_CHARS)
        if not text.strip():
            raise _FormError("Scanner output is required.")
        created = _create_intake_findings(engagement["id"], parse_intake(text))
    except _FormError as exc:
        flash(str(exc), "error")
        return redirect(_engagement_url(engagement["id"]))
    flash(f"Imported {created} scanner candidate(s) as draft findings.", "info")
    return redirect(_engagement_url(engagement["id"]))


@bp.route("/audit/engagements/<engagement_id>/run", methods=["POST"])
@limiter.limit("6 per minute")
def audit_tool_run(engagement_id: str):
    """Run one hardened profile and save its exact output for one later import."""
    engagement = _engagement_or_404(engagement_id)
    try:
        profile = _form_text("profile", 64, strip=True)
        target = _form_text("target", 1024)
        wordlist = _form_text("wordlist", 1024)
        if not profile:
            raise _FormError("Select a tool profile.")
        result = runner.run_profile(profile, target=target, wordlist=wordlist)
    except (ValueError, runner.RunCapacityError) as exc:
        flash(str(exc), "error")
        return redirect(_engagement_url(engagement["id"]))

    candidates = parse_intake(result.output) if result.output else []
    _save_run(engagement["id"], result, candidates)
    return _render_engagement(
        engagement["id"], run_preview=result, run_candidates=candidates
    )


@bp.route(
    "/audit/engagements/<engagement_id>/runs/<run_id>/import",
    methods=["POST"],
)
@limiter.limit("20 per minute")
def audit_tool_run_import(engagement_id: str, run_id: str):
    """Import candidates from the saved run without executing the tool again."""
    engagement = _engagement_or_404(engagement_id)
    _entity_id_or_404(run_id)
    try:
        saved = _consume_run(engagement["id"], run_id)
        candidates = json.loads(saved.candidates_json)
        created = _create_candidates(engagement["id"], candidates)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(_engagement_url(engagement["id"]))
    flash(
        f"Imported {len(created)} structured candidate(s) as draft findings.",
        "info",
    )
    return redirect(_engagement_url(engagement["id"]))


@bp.route("/audit/engagements/<engagement_id>/report.md")
@limiter.limit("30 per minute")
def audit_report_download(engagement_id: str):
    """Download the current engagement report as Markdown."""
    engagement = _engagement_or_404(engagement_id)
    markdown = engagement_report(
        engagement,
        current_app.audit_store.list_findings(engagement["id"]),
        current_app.audit_store.engagement_stats(engagement["id"]),
    )
    return Response(
        markdown,
        mimetype="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="report-{engagement["id"][:8]}.md"'
            )
        },
    )
