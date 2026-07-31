"""Tests for intake parsing of pasted scanner output and notes."""

from app.audit.parse import parse_intake


def test_empty_input_returns_no_candidates():
    assert parse_intake("") == []
    assert parse_intake("   \n  ") == []


def test_bracketed_severity_lines():
    text = "[HIGH] Missing access control in withdraw\n[LOW] Unused return value\n"
    candidates = parse_intake(text)
    assert len(candidates) == 2
    assert candidates[0]["severity"] == "high"
    assert candidates[0]["title"] == "Missing access control in withdraw"
    assert candidates[1]["severity"] == "low"


def test_plain_severity_colon_lines():
    text = "Critical: Reentrancy in claim()\nMedium: Oracle staleness not checked\n"
    candidates = parse_intake(text)
    assert [c["severity"] for c in candidates] == ["critical", "medium"]


def test_informational_and_gas_aliases():
    text = "[Informational] Naming convention\n[Optimization] Cache array length\n"
    candidates = parse_intake(text)
    assert [c["severity"] for c in candidates] == ["info", "gas"]


def test_detail_lines_attach_to_finding_and_location_extracted():
    text = (
        "[HIGH] Reentrancy allows double claim\n"
        "The claim function updates state after the external call.\n"
        "contracts/Vault.sol#L42-58\n"
        "[LOW] Missing event\n"
    )
    candidates = parse_intake(text)
    assert len(candidates) == 2
    first = candidates[0]
    assert "external call" in first["description"]
    assert first["target"] == "contracts/Vault.sol#L42-58"
    assert candidates[1]["target"] == ""


def test_freeform_fallback_single_candidate():
    text = "Some unformatted auditor notes\nspanning multiple lines."
    candidates = parse_intake(text)
    assert len(candidates) == 1
    assert candidates[0]["severity"] == "info"
    assert candidates[0]["description"] == text.strip()
    assert candidates[0]["title"] == "Some unformatted auditor notes"


def test_titles_are_capped():
    text = "[HIGH] " + "x" * 500
    candidates = parse_intake(text)
    assert len(candidates[0]["title"]) <= 200
