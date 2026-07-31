#!/usr/bin/env python3
"""Run a one-pass audit over a local code path and record structured findings.

Usage:
    python3 tools/audit_run.py --engagement NAME --path PATH [--focus TEXT]
                               [--consent-external] [--no-verify] [--strict] [--json]

The loop follows the V12 shape: analyze with memory, generate an executable
PoC candidate, verify its exact artifact, and record honestly. Findings whose
PoC passes are created as "triaged". Findings the harness cannot verify stay
"draft" with the verification verdict recorded in the description. ``--strict``
stores only findings whose exact generated PoC artifact passes verification.

The analysis and PoC passes transmit bounded source text to the configured
external model pool. That transmission happens only when the caller passes
``--consent-external``; without it the run fails before any model call.

Model access is configured through the environment (see app.models.pool).
Exit code 2 means the run itself failed; findings never affect the exit code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audit.agent import analyze, generate_poc  # noqa: E402
from app.audit.runner import validate_path_target, workspace_roots  # noqa: E402
from app.audit.store import AuditStore  # noqa: E402
from app.audit.verify import verify_poc  # noqa: E402
from app.models.pool import ModelError, ModelPool  # noqa: E402

SUPPORTED_EXTENSIONS = {".sol", ".rs", ".go", ".py", ".ts", ".js"}

# Vendored dependency and build-output directories are noise for a first
# pass, not audit targets. Foundry's lib/ holds other people's code.
SKIP_DIRS = {".git", "node_modules", "out", "cache", "forge-cache", "lib"}


def collect_files(root: Path) -> tuple[list[dict], list[str]]:
    """Read supported source files under root, sorted for determinism.

    Returns (files, skipped): files are {"path", "content"} dicts, skipped
    lists paths that failed UTF-8 decoding so the run reports them honestly.
    """
    files: list[dict] = []
    skipped: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.suffix not in SUPPORTED_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append(str(path))
            continue
        files.append({"path": str(path.relative_to(root)), "content": content})
    return files, skipped


def _require_workspace_configuration() -> None:
    """Reject incomplete workspace-root configuration before source access."""
    raw = os.environ.get("AUDIT_WORKSPACE_ROOTS", "")
    configured = raw.split(os.pathsep)
    if not raw.strip() or any(not part.strip() for part in configured):
        raise ValueError("AUDIT_WORKSPACE_ROOTS must name existing directories.")
    if len(workspace_roots()) != len(configured):
        raise ValueError("Every AUDIT_WORKSPACE_ROOTS entry must be an existing directory.")


def _engagement_for(store: AuditStore, name: str) -> dict:
    for engagement in store.list_engagements():
        if engagement["name"] == name:
            return engagement
    engagement_id = store.create_engagement(name=name, platform="self")
    return store.get_engagement(engagement_id)


def _record(store: AuditStore, engagement_id: str, finding: dict, **overrides: str) -> str:
    payload = {**finding, **overrides}
    return store.create_finding(
        engagement_id,
        title=payload["title"],
        severity=payload["severity"],
        status=payload.get("status", "draft"),
        target=payload.get("target", ""),
        description=payload.get("description", ""),
        impact=payload.get("impact", ""),
        poc=payload.get("poc", ""),
        remediation=payload.get("remediation", ""),
    )


def _verify_findings(
    root: Path,
    files: list[dict],
    findings: list[dict],
    pool: ModelPool,
    *,
    external_consent: bool,
) -> list[dict]:
    """Attach a PoC and a verification verdict to each finding."""
    verified: list[dict] = []
    for finding in findings:
        record = dict(finding)
        try:
            poc = generate_poc(files, finding, pool=pool, external_consent=external_consent)
        except (ModelError, ValueError) as exc:
            record["verification"] = {"status": "unverified", "reason": str(exc)}
            verified.append(record)
            continue
        record["poc"] = poc["source"]
        verdict = verify_poc(root, poc["contract_name"], poc["source"])
        expected_source_sha256 = hashlib.sha256(poc["source"].encode("utf-8")).hexdigest()
        artifact_sha256 = verdict.get("artifact_sha256")
        exact_artifact = (
            verdict.get("source_sha256") == expected_source_sha256
            and isinstance(artifact_sha256, str)
            and len(artifact_sha256) == 64
            and all(character in "0123456789abcdef" for character in artifact_sha256)
        )
        if verdict.get("status") == "verified" and not exact_artifact:
            verdict = {
                **verdict,
                "status": "unverified",
                "reason": "verification did not identify the exact generated PoC artifact",
            }
        record["verification"] = verdict
        verified.append(record)
    return verified


def main(argv: list[str] | None = None, *, pool: ModelPool | None = None,
         store: AuditStore | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engagement", required=True, help="engagement name (created if new)")
    parser.add_argument("--path", required=True, help="code path to audit")
    parser.add_argument("--focus", default="", help="extra instruction for the analysis pass")
    parser.add_argument(
        "--consent-external",
        action="store_true",
        help="consent to transmitting source to the configured external model pool",
    )
    parser.add_argument("--no-verify", action="store_true", help="skip PoC generation/execution")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="store only findings with an exactly verified PoC artifact",
    )
    parser.add_argument("--json", action="store_true", help="print a machine-readable summary")
    args = parser.parse_args(argv)

    try:
        _require_workspace_configuration()
        root = validate_path_target(args.path)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: invalid audit path: {exc}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    pool = pool or ModelPool.from_env()
    store = store or AuditStore()

    files, skipped = collect_files(root)
    if not files:
        print(f"error: no supported source files under {root}", file=sys.stderr)
        return 2

    engagement = _engagement_for(store, args.engagement)
    prior = store.list_findings(engagement["id"])
    try:
        result = analyze(files, pool=pool, prior_findings=prior, focus=args.focus,
                         external_consent=args.consent_external)
    except (ModelError, ValueError) as exc:
        print(f"error: analysis failed: {exc}", file=sys.stderr)
        return 2

    findings = result["findings"]
    can_verify = not args.no_verify and (root / "foundry.toml").is_file()
    if can_verify:
        findings = _verify_findings(root, files, findings, pool,
                                    external_consent=args.consent_external)
    else:
        reason = (
            "verification was explicitly skipped by --no-verify"
            if args.no_verify
            else "verification requires a Foundry project"
        )
        findings = [
            {**finding, "verification": {"status": "unverified", "reason": reason}}
            for finding in findings
        ]

    created: list[str] = []
    suppressed = 0
    for finding in findings:
        verdict = finding.get("verification", {})
        if args.strict and verdict.get("status") != "verified":
            suppressed += 1
            continue
        overrides: dict[str, str] = {"poc": finding.get("poc", "")}
        if verdict.get("status") == "verified":
            overrides["status"] = "triaged"
        elif verdict.get("status") in ("unproven", "unverified"):
            note = f"[verification: {verdict['status']} — {verdict['reason']}]"
            overrides["description"] = f"{note}\n\n{finding['description']}"
        created.append(_record(store, engagement["id"], finding, **overrides))

    verified_count = sum(
        1 for f in findings if f.get("verification", {}).get("status") == "verified"
    )
    summary = {
        "engagement_id": engagement["id"],
        "scope_files": len(files),
        "skipped_files": skipped,
        "findings": len(created),
        "verified": verified_count,
        "suppressed_strict": suppressed,
        "dropped_unparseable": result["dropped"],
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Engagement: {engagement['name']} ({engagement['id']})")
        skipped_note = f", skipped {len(skipped)} undecodable" if skipped else ""
        print(f"Scope: {len(files)} files{skipped_note}")
        print(f"Findings recorded: {len(created)} ({verified_count} with a verified PoC)")
        if suppressed:
            print(f"Suppressed without an exactly verified PoC (--strict): {suppressed}")
        if result["dropped"]:
            print(f"Dropped for failing the output contract: {result['dropped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
