"""Foundry PoC test skeleton generation for audit findings.

Renders a ready-to-fill ``forge test`` contract so a finding can be proven
quickly. Pure string templating; no subprocess or filesystem access.
"""
from __future__ import annotations

import re

_IDENT_RE = re.compile(r"[^A-Za-z0-9]+")


def _contract_name(title: str) -> str:
    """Derive a valid Solidity identifier suffix from a finding title."""
    words = [word for word in _IDENT_RE.split(title) if word]
    suffix = "".join(word.capitalize() for word in words[:6]) or "Finding"
    if suffix[0].isdigit():
        suffix = f"F{suffix}"
    return f"{suffix}PoC"


def _one_line(value: object) -> str:
    """Collapse untrusted text so it cannot end a Solidity line comment."""
    return " ".join(str(value).splitlines())


def _target_path(target: str) -> str:
    """Return a one-line target path without a #Lx suffix."""
    return _one_line(target).split("#", 1)[0]


def poc_template(finding: dict, engagement: dict | None = None) -> str:
    """Render a Foundry test skeleton for one finding.

    Args:
        finding: Finding dict with title, target, severity, description, poc.
        engagement: Optional engagement dict; its name appears in the header.
    """
    title = _one_line(finding["title"])
    severity = _one_line(finding["severity"])
    contract = _contract_name(title)
    target = _target_path(finding.get("target", ""))
    engagement_name = _one_line(engagement["name"]) if engagement else "engagement"
    lines = [
        "// SPDX-License-Identifier: UNLICENSED",
        "pragma solidity ^0.8.0;",
        "",
        'import "forge-std/Test.sol";',
    ]
    if target:
        lines.append(f'// import "../src/{target}";  // adjust path to the target')
    lines += [
        "",
        f"/// @title PoC: {title}",
        f"/// @notice Engagement: {engagement_name} | Severity: {severity}",
    ]
    if finding.get("description"):
        first_line = _one_line(str(finding["description"]).splitlines()[0])[:200]
        lines.append(f"/// @dev {first_line}")
    lines += [
        f"contract {contract} is Test {{",
        "    function setUp() public {",
        "        // Deploy or fork the target contract here.",
        "        // vm.createSelectFork(vm.rpcUrl(\"mainnet\"));",
        "    }",
        "",
        "    function test_exploit() public {",
        "        // 1. Arrange: put the system in the vulnerable state.",
    ]
    if finding.get("poc"):
        lines.append("        //")
        for poc_line in finding["poc"].splitlines()[:20]:
            lines.append(f"        // {poc_line}")
    lines += [
        "        // 2. Act: trigger the vulnerability.",
        "        // 3. Assert: prove the impact (stolen funds, broken invariant).",
        '        // assertEq(attacker.balance, expected);',
        "    }",
        "}",
        "",
    ]
    return "\n".join(lines)
