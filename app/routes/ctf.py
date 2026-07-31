"""CTF workspace routes: events, challenges, notes, and the flag vault."""

import re

from flask import (
    Response, abort, current_app, flash, redirect, render_template, request, url_for,
)

from app import limiter
from app.ctf import CATEGORIES, DIFFICULTIES, STATUSES
from app.ctf import runner
from app.ctf.flags import FLAG_PATTERN, MAX_FLAG_LENGTH
from app.ctf.hints import hints_for
from app.ctf.writeup import challenge_writeup, event_writeup

from . import bp

_EVENT_NAME_MAX = 120
_EVENT_URL_MAX = 500
_CHALLENGE_NAME_MAX = 160
_DESCRIPTION_MAX = 4000
_NOTE_MAX = 8000
_POINTS_MAX = 100000


def _clean(value: str | None, max_length: int) -> str:
    return (value or "").strip()[:max_length]


def _parse_points(raw: str | None) -> int | None:
    """Parse a non-negative points value; None when invalid."""
    try:
        points = int((raw or "0").strip() or "0")
    except ValueError:
        return None
    if points < 0 or points > _POINTS_MAX:
        return None
    return points


def _is_valid_flag(value: str) -> bool:
    return bool(value) and len(value) <= MAX_FLAG_LENGTH and bool(
        FLAG_PATTERN.fullmatch(value)
    )


def _get_challenge_or_404(challenge_id: str) -> dict:
    challenge = current_app.ctf_store.get_challenge(challenge_id)
    if challenge is None:
        abort(404)
    return challenge


def _challenge_url(challenge_id: str) -> str:
    return url_for("main.ctf_challenge_detail", challenge_id=challenge_id)


@bp.route("/ctf")
@limiter.limit("30 per minute")
def ctf_events_list():
    """List CTF events with progress counts."""
    return render_template(
        "ctf_events.html",
        events=current_app.ctf_store.list_events(),
    )


@bp.route("/ctf/events", methods=["POST"])
@limiter.limit("10 per minute")
def ctf_event_create():
    """Create a CTF event."""
    name = _clean(request.form.get("name"), _EVENT_NAME_MAX)
    url = _clean(request.form.get("url"), _EVENT_URL_MAX)
    if not name:
        flash("Event name is required.", "error")
        return redirect(url_for("main.ctf_events_list"))
    if url and not url.startswith(("http://", "https://")):
        flash("Event URL must start with http:// or https://.", "error")
        return redirect(url_for("main.ctf_events_list"))
    event_id = current_app.ctf_store.create_event(name, url)
    return redirect(url_for("main.ctf_event_detail", event_id=event_id))


@bp.route("/ctf/events/<event_id>")
@limiter.limit("30 per minute")
def ctf_event_detail(event_id: str):
    """Event detail: challenge board plus add-challenge form."""
    event = current_app.ctf_store.get_event(event_id)
    if event is None:
        abort(404)
    return render_template(
        "ctf_event.html",
        event=event,
        challenges=current_app.ctf_store.list_challenges(event_id),
        stats=current_app.ctf_store.event_stats(event_id),
        categories=CATEGORIES,
        difficulties=DIFFICULTIES,
        statuses=STATUSES,
    )


@bp.route("/ctf/events/<event_id>/delete", methods=["POST"])
@limiter.limit("10 per minute")
def ctf_event_delete(event_id: str):
    """Delete an event and its challenges."""
    current_app.ctf_store.delete_event(event_id)
    flash("Event deleted.", "info")
    return redirect(url_for("main.ctf_events_list"))


@bp.route("/ctf/events/<event_id>/challenges", methods=["POST"])
@limiter.limit("10 per minute")
def ctf_challenge_create(event_id: str):
    """Add a challenge to an event."""
    if current_app.ctf_store.get_event(event_id) is None:
        abort(404)
    fallback_url = url_for("main.ctf_event_detail", event_id=event_id)
    name = _clean(request.form.get("name"), _CHALLENGE_NAME_MAX)
    category = _clean(request.form.get("category"), 32)
    difficulty = _clean(request.form.get("difficulty"), 16) or "unknown"
    description = _clean(request.form.get("description"), _DESCRIPTION_MAX)
    points = _parse_points(request.form.get("points"))
    if not name or category not in CATEGORIES:
        flash("A challenge name and valid category are required.", "error")
        return redirect(fallback_url)
    if difficulty not in DIFFICULTIES or points is None:
        flash("Invalid difficulty or points value.", "error")
        return redirect(fallback_url)
    challenge_id = current_app.ctf_store.create_challenge(
        event_id, name, category, difficulty, points, description
    )
    return redirect(_challenge_url(challenge_id))


@bp.route("/ctf/challenges/<challenge_id>")
@limiter.limit("30 per minute")
def ctf_challenge_detail(challenge_id: str):
    """Challenge detail: notes timeline and flag vault."""
    challenge = _get_challenge_or_404(challenge_id)
    return render_template(
        "ctf_challenge.html",
        challenge=challenge,
        event=current_app.ctf_store.get_event(challenge["event_id"]),
        notes=current_app.ctf_store.list_notes(challenge_id),
        flags=current_app.ctf_store.list_flags(challenge_id),
        runs=current_app.ctf_store.list_runs(challenge_id),
        profiles=runner.available_profiles(),
        hints=hints_for(challenge["category"]),
        statuses=STATUSES,
    )


@bp.route("/ctf/challenges/<challenge_id>/notes", methods=["POST"])
@limiter.limit("10 per minute")
def ctf_note_add(challenge_id: str):
    """Add a note; flag-shaped tokens are captured into the vault."""
    _get_challenge_or_404(challenge_id)
    body = _clean(request.form.get("body"), _NOTE_MAX)
    if not body:
        flash("Note text is required.", "error")
        return redirect(_challenge_url(challenge_id))
    _, detected = current_app.ctf_store.add_note(challenge_id, body)
    if detected:
        flash(f"Captured {len(detected)} flag-shaped token(s) into the vault.", "info")
    return redirect(_challenge_url(challenge_id))


@bp.route("/ctf/challenges/<challenge_id>/flags", methods=["POST"])
@limiter.limit("10 per minute")
def ctf_flag_add(challenge_id: str):
    """Submit a flag; marks the challenge solved."""
    _get_challenge_or_404(challenge_id)
    flag = _clean(request.form.get("flag"), MAX_FLAG_LENGTH)
    if not _is_valid_flag(flag):
        flash("Flags must look like PREFIX{...}.", "error")
        return redirect(_challenge_url(challenge_id))
    inserted = current_app.ctf_store.add_flag(challenge_id, flag)
    current_app.ctf_store.set_challenge_status(challenge_id, "solved")
    flash("Flag recorded — challenge marked solved." if inserted else
          "Flag was already in the vault — challenge marked solved.", "info")
    return redirect(_challenge_url(challenge_id))


def _markdown_response(body: str, filename: str) -> Response:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-.") or "writeup.md"
    return Response(
        body,
        mimetype="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@bp.route("/ctf/challenges/<challenge_id>/writeup.md")
@limiter.limit("30 per minute")
def ctf_challenge_writeup(challenge_id: str):
    """Download a markdown writeup for one challenge."""
    challenge = _get_challenge_or_404(challenge_id)
    body = challenge_writeup(
        current_app.ctf_store.get_event(challenge["event_id"]),
        challenge,
        current_app.ctf_store.list_notes(challenge_id),
        current_app.ctf_store.list_flags(challenge_id),
        current_app.ctf_store.list_runs(challenge_id),
    )
    return _markdown_response(body, f"writeup-{challenge['name'][:40]}.md")


@bp.route("/ctf/events/<event_id>/writeup.md")
@limiter.limit("30 per minute")
def ctf_event_writeup(event_id: str):
    """Download a markdown writeup for a whole event."""
    event = current_app.ctf_store.get_event(event_id)
    if event is None:
        abort(404)
    sections = []
    for challenge in current_app.ctf_store.list_challenges(event_id):
        sections.append(
            challenge_writeup(
                event,
                challenge,
                current_app.ctf_store.list_notes(challenge["id"]),
                current_app.ctf_store.list_flags(challenge["id"]),
                current_app.ctf_store.list_runs(challenge["id"]),
            )
        )
    body = event_writeup(event, sections, current_app.ctf_store.event_stats(event_id))
    return _markdown_response(body, f"writeup-{event['name'][:40]}.md")


@bp.route("/ctf/challenges/<challenge_id>/runs", methods=["POST"])
@limiter.limit("5 per minute")
def ctf_run_create(challenge_id: str):
    """Execute one allowlisted recon profile and record the run."""
    _get_challenge_or_404(challenge_id)
    profile = _clean(request.form.get("profile"), 64)
    target = _clean(request.form.get("target"), 253)
    wordlist = _clean(request.form.get("wordlist"), 200)
    try:
        result = runner.run_profile(profile, target, wordlist)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(_challenge_url(challenge_id))
    current_app.ctf_store.add_run(
        challenge_id, profile, result.argv, result.exit_code, result.output, result.error
    )
    if result.flags:
        flash(f"Run captured {len(result.flags)} flag-shaped token(s).", "info")
    elif result.error:
        flash(f"Run failed: {result.error}", "error")
    else:
        flash(f"Run finished with exit code {result.exit_code}.", "info")
    return redirect(_challenge_url(challenge_id))


@bp.route("/ctf/challenges/<challenge_id>/status", methods=["POST"])
@limiter.limit("10 per minute")
def ctf_challenge_status(challenge_id: str):
    """Update a challenge's status."""
    _get_challenge_or_404(challenge_id)
    status = _clean(request.form.get("status"), 16)
    if status not in STATUSES:
        flash("Invalid status.", "error")
        return redirect(_challenge_url(challenge_id))
    current_app.ctf_store.set_challenge_status(challenge_id, status)
    return redirect(_challenge_url(challenge_id))


@bp.route("/ctf/challenges/<challenge_id>/delete", methods=["POST"])
@limiter.limit("10 per minute")
def ctf_challenge_delete(challenge_id: str):
    """Delete a challenge and return to its event."""
    challenge = _get_challenge_or_404(challenge_id)
    current_app.ctf_store.delete_challenge(challenge_id)
    flash("Challenge deleted.", "info")
    return redirect(url_for("main.ctf_event_detail", event_id=challenge["event_id"]))
