"""Markdown writeup generation for CTF challenges and events."""
from __future__ import annotations


def _fence(text: str) -> str:
    """Wrap text in a code fence that cannot be closed by its content."""
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}\n{text}\n{fence}"


def challenge_writeup(
    event: dict | None,
    challenge: dict,
    notes: list[dict],
    flags: list[dict],
    runs: list[dict],
) -> str:
    """Render a single challenge as a markdown writeup."""
    lines = [
        f"# {challenge['name']}",
        "",
        f"- Event: {event['name'] if event else 'unknown'}",
        f"- Category: {challenge['category']}",
        f"- Difficulty: {challenge['difficulty']}",
        f"- Points: {challenge['points']}",
        f"- Status: {challenge['status']}",
        "",
    ]
    if challenge.get("description"):
        lines += ["## Description", "", challenge["description"], ""]
    if flags:
        lines += ["## Flags", ""]
        for entry in reversed(flags):
            lines.append(f"- `{entry['flag']}` (via {entry['source']}, {entry['created_at'][:10]})")
        lines.append("")
    if notes:
        lines += ["## Notes", ""]
        for note in reversed(notes):
            lines += [f"### {note['created_at'][:16].replace('T', ' ')} UTC", ""]
            lines += [_fence(note["body"]), ""]
    if runs:
        lines += ["## Tool runs", ""]
        for run in reversed(runs):
            lines += [
                f"### {run['profile']} — exit {run['exit_code']} "
                f"({run['created_at'][:16].replace('T', ' ')} UTC)",
                "",
                f"`{' '.join(run['argv'])}`",
                "",
            ]
            if run["error"]:
                lines += [f"Error: {run['error']}", ""]
            if run["output"]:
                lines += [_fence(run["output"]), ""]
    return "\n".join(lines).rstrip() + "\n"


def event_writeup(event: dict, sections: list[str], stats: dict) -> str:
    """Render a whole event: title, scoreboard, then per-challenge writeups."""
    lines = [
        f"# {event['name']} — writeup",
        "",
        f"- URL: {event['url'] or 'n/a'}",
        f"- Solved: {stats['solved']}/{stats['total']}",
        f"- Points: {stats['points']}",
        "",
        "---",
        "",
    ]
    lines += sections
    return "\n".join(lines).rstrip() + "\n"
