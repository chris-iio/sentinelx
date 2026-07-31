"""Bounded external-model support for audit review.

Both public functions transmit source text to an external model pool. They do
nothing unless the caller gives explicit consent for that transmission. Only
validated and bounded fields enter a prompt. Model findings are hypotheses;
they need reproducible verification before an analyst treats them as proven.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any, Protocol

from .poc import _contract_name, poc_template
from .store import SEVERITIES

__all__ = (
    "MAX_FILE_BYTES",
    "MAX_FILES",
    "MAX_MODEL_OUTPUT_BYTES",
    "MAX_TOTAL_BYTES",
    "analyze",
    "generate_poc",
)

MAX_FILES = 50
MAX_FILE_BYTES = 100_000
MAX_TOTAL_BYTES = 200_000
MAX_MODEL_OUTPUT_BYTES = 100_000
MAX_FINDINGS = 100
MAX_PRIOR_FINDINGS = 100
MAX_PATH_CHARS = 512
MAX_FOCUS_BYTES = 2_000
MAX_POC_OUTPUT_BYTES = 256 * 1024

_TASK_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_LINE_TARGET_RE = re.compile(r"(?P<path>[^#]+)(?:#L(?P<line>[1-9][0-9]{0,8}))?\Z")
_FINDING_KEYS = frozenset(
    {"title", "severity", "target", "description", "impact", "remediation"}
)
_FINDING_LIMITS = {
    "title": 200,
    "target": 1_024,
    "description": 8_000,
    "impact": 4_000,
    "remediation": 4_000,
}
_PRIOR_TITLE_BYTES = 500
_PRIOR_STATUS_BYTES = 100


class ModelPool(Protocol):
    """Small interface used by the configured external model pool."""

    def complete(self, task: str, system: str, user: str) -> str:
        """Return one model response."""


_SYSTEM_PROMPT = """You are a security reviewer performing an authorized audit of the user's
own code.

Every model finding is an unverified hypothesis until a reproducible check
proves it. Report only concrete issues you can point to specific supplied code
for. Do not report speculative style concerns, missing-documentation notes, or
issues you cannot locate. Prefer a short list of real issues over many maybes.

Respond with a JSON array and nothing else. Each element must be an object with
exactly these string fields:
- "title": one sentence naming the issue
- "severity": one of "critical", "high", "medium", "low", "info", "gas"
- "target": a supplied file path, optionally with a "#L<line>" suffix
- "description": what the code does wrong, with the concrete call path
- "impact": what an attacker or unlucky user gains or loses
- "remediation": the smallest change that removes the issue

Report an empty array when the code is clean."""

_POC_SYSTEM_PROMPT = """You are writing an executable proof of concept for an authorized audit
of the user's own code.

The finding is an unverified hypothesis. Complete the Foundry test skeleton so
the exploit can be checked against the supplied code. Keep the contract name
from the skeleton. Respond with the complete Solidity test file and nothing
else."""

_FENCE_RE = re.compile(r"```(?:solidity|sol)\s*\n(?P<source>.*?)\n```\s*\Z", re.DOTALL)


def _require_external_consent(external_consent: bool) -> None:
    if external_consent is not True:
        raise ValueError("explicit external transmission consent is required")


def _validate_task(task: str) -> str:
    if not isinstance(task, str) or not _TASK_RE.fullmatch(task):
        raise ValueError("task must be a simple identifier (max 64 chars)")
    return task


def _utf8_size(value: str) -> int:
    return len(value.encode("utf-8"))


def _validate_path(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("file path must be text")
    if not value or len(value) > MAX_PATH_CHARS or "\x00" in value or "\\" in value:
        raise ValueError("file path is empty, too long, or contains an unsafe character")
    if any(ord(character) < 32 for character in value):
        raise ValueError("file path contains a control character")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("/"):
        raise ValueError(f"absolute file path is not allowed: {value}")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError(f"file path traversal is not allowed: {value}")
    if path.as_posix() != value:
        raise ValueError(f"file path is not normalized: {value}")
    return value


def _validate_files(files: object) -> list[dict[str, str]]:
    if not isinstance(files, list):
        raise ValueError("files must be a list")
    if not files:
        raise ValueError("at least one source file is required")
    if len(files) > MAX_FILES:
        raise ValueError(f"scope has {len(files)} files; the limit is {MAX_FILES}")

    validated: list[dict[str, str]] = []
    seen: set[str] = set()
    total = 0
    for index, record in enumerate(files):
        if not isinstance(record, dict) or set(record) != {"path", "content"}:
            raise ValueError(f"file record {index} must contain only path and content")
        path = _validate_path(record["path"])
        if path in seen:
            raise ValueError(f"duplicate file path: {path}")
        content = record["content"]
        if not isinstance(content, str):
            raise ValueError(f"file content must be text: {path}")
        if "\x00" in content:
            raise ValueError(f"file content contains NUL: {path}")
        size = _utf8_size(content)
        if size > MAX_FILE_BYTES:
            raise ValueError(f"file exceeds {MAX_FILE_BYTES} UTF-8 bytes: {path}")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ValueError(
                f"scope has more than {MAX_TOTAL_BYTES} UTF-8 bytes"
            )
        seen.add(path)
        validated.append({"path": path, "content": content})
    return validated


def _bounded_text(value: object, field: str, limit: int, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    text = value.strip()
    if required and not text:
        raise ValueError(f"{field} is required")
    if "\x00" in text or _utf8_size(text) > limit:
        raise ValueError(f"{field} is unsafe or exceeds {limit} UTF-8 bytes")
    return text


def _validate_focus(focus: object) -> str:
    return _bounded_text(focus, "focus", MAX_FOCUS_BYTES, required=False)


def _validate_prior_findings(prior_findings: object) -> list[dict[str, str]]:
    if prior_findings is None:
        return []
    if not isinstance(prior_findings, list):
        raise ValueError("prior_findings must be a list")
    if len(prior_findings) > MAX_PRIOR_FINDINGS:
        raise ValueError(f"prior_findings exceeds {MAX_PRIOR_FINDINGS} records")

    validated: list[dict[str, str]] = []
    for index, finding in enumerate(prior_findings):
        if not isinstance(finding, dict):
            raise ValueError(f"prior finding {index} must be an object")
        title = _bounded_text(
            finding.get("title"), f"prior finding {index} title", _PRIOR_TITLE_BYTES
        )
        status = _bounded_text(
            finding.get("status", "draft"),
            f"prior finding {index} status",
            _PRIOR_STATUS_BYTES,
        )
        validated.append({"title": title, "status": status})
    return validated


def _prior_section(prior_findings: list[dict[str, str]]) -> str:
    lines = ["Previously reported findings — do not report these again:"]
    lines.extend(f"- [{finding['status']}] {finding['title']}" for finding in prior_findings)
    return "\n".join(lines)


def _files_section(files: list[dict[str, str]]) -> str:
    return "\n\n".join(f"--- {item['path']} ---\n{item['content']}" for item in files)


def _user_prompt(
    files: list[dict[str, str]], prior_findings: list[dict[str, str]], focus: str
) -> str:
    parts: list[str] = []
    if focus:
        parts.append(f"Audit focus from the reviewer: {focus}")
    if prior_findings:
        parts.append(_prior_section(prior_findings))
    parts.append("Code under audit:\n" + _files_section(files))
    return "\n\n".join(parts)


def _validate_model_response(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError("model response must be text")
    if _utf8_size(raw) > MAX_MODEL_OUTPUT_BYTES:
        raise ValueError(f"model response exceeds {MAX_MODEL_OUTPUT_BYTES} UTF-8 bytes")
    return raw


def _parse_json_array(raw: str) -> tuple[list[Any], bool]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return [], True
    if not isinstance(value, list) or len(value) > MAX_FINDINGS:
        return [], True
    return value, False


def _normalize_finding(item: Any, paths: set[str]) -> dict[str, str] | None:
    if not isinstance(item, dict) or set(item) != _FINDING_KEYS:
        return None
    if any(not isinstance(item[key], str) for key in _FINDING_KEYS):
        return None
    severity = item["severity"].strip()
    if severity not in SEVERITIES:
        return None

    normalized: dict[str, str] = {"severity": severity}
    for field, limit in _FINDING_LIMITS.items():
        value = item[field].strip()
        if not value or "\x00" in value or _utf8_size(value) > limit:
            return None
        normalized[field] = value

    target_match = _LINE_TARGET_RE.fullmatch(normalized["target"])
    if target_match is None or target_match.group("path") not in paths:
        return None
    return {
        "title": normalized["title"],
        "severity": normalized["severity"],
        "target": normalized["target"],
        "description": normalized["description"],
        "impact": normalized["impact"],
        "remediation": normalized["remediation"],
    }


def analyze(
    files: list[dict],
    *,
    pool: ModelPool,
    external_consent: bool = False,
    task: str = "analysis",
    prior_findings: list[dict] | None = None,
    focus: str = "",
    include_raw: bool = False,
) -> dict:
    """Send a bounded source scope for one consented external model pass.

    The return value omits raw model text unless ``include_raw`` is true.
    Returned findings are model hypotheses, not verified vulnerabilities.
    """
    _require_external_consent(external_consent)
    validated_files = _validate_files(files)
    validated_prior = _validate_prior_findings(prior_findings)
    validated_focus = _validate_focus(focus)
    validated_task = _validate_task(task)

    raw = _validate_model_response(
        pool.complete(
            validated_task,
            _SYSTEM_PROMPT,
            _user_prompt(validated_files, validated_prior, validated_focus),
        )
    )
    items, parse_error = _parse_json_array(raw)
    paths = {item["path"] for item in validated_files}
    findings = [
        finding
        for finding in (_normalize_finding(item, paths) for item in items)
        if finding is not None
    ]
    result = {
        "findings": findings,
        "dropped": len(items) - len(findings),
        "parse_error": parse_error,
        "response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }
    if include_raw:
        result["raw"] = raw
    return result


def _validate_poc_finding(finding: object) -> dict[str, str]:
    if not isinstance(finding, dict):
        raise ValueError("finding must be an object")
    validated: dict[str, str] = {}
    for field, limit in _FINDING_LIMITS.items():
        validated[field] = _bounded_text(finding.get(field), f"finding {field}", limit)
    severity = _bounded_text(finding.get("severity"), "finding severity", 20)
    if severity not in SEVERITIES:
        raise ValueError("finding severity is invalid")
    validated["severity"] = severity
    if "poc" in finding:
        validated["poc"] = _bounded_text(
            finding["poc"], "finding poc", 8_000, required=False
        )
    return validated


def _strict_poc_source(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError("model response must be text")
    if _utf8_size(raw) > MAX_POC_OUTPUT_BYTES:
        raise ValueError(f"model PoC exceeds {MAX_POC_OUTPUT_BYTES} UTF-8 bytes")
    match = _FENCE_RE.fullmatch(raw.strip())
    source = match.group("source").strip() if match else raw.strip()
    if not source or "\x00" in source or "```" in source:
        raise ValueError("model PoC response is empty or not strict Solidity text")
    return source


def generate_poc(
    files: list[dict],
    finding: dict,
    *,
    pool: ModelPool,
    external_consent: bool = False,
    task: str = "poc",
) -> dict:
    """Generate one untrusted PoC after explicit external transmission consent."""
    _require_external_consent(external_consent)
    validated_files = _validate_files(files)
    validated_finding = _validate_poc_finding(finding)
    validated_task = _validate_task(task)
    skeleton = poc_template(validated_finding)
    user = (
        "Finding (unverified hypothesis):\n"
        + json.dumps(validated_finding, indent=2)
        + "\n\nCode under audit:\n"
        + _files_section(validated_files)
        + "\n\nTest skeleton to complete:\n"
        + skeleton
    )
    source = _strict_poc_source(pool.complete(validated_task, _POC_SYSTEM_PROMPT, user))
    return {
        "source": source,
        "contract_name": _contract_name(validated_finding["title"]),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }
