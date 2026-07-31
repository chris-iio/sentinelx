"""Tests for Foundry PoC test skeleton generation."""

from app.audit.poc import _contract_name, poc_template


def _finding(**overrides):
    finding = {
        "title": "Reentrancy in claim",
        "severity": "high",
        "target": "contracts/Vault.sol#L42-58",
        "description": "State updated after external call.\nSecond line.",
        "poc": "vault.claim();\nvault.claim();",
    }
    finding.update(overrides)
    return finding


def test_contract_name_from_title():
    assert _contract_name("Reentrancy in claim") == "ReentrancyInClaimPoC"
    assert _contract_name("!!!") == "FindingPoC"
    assert _contract_name("123 go") == "F123GoPoC"


def test_template_structure():
    source = poc_template(_finding(), {"name": "Code4rena — Example"})
    assert "pragma solidity ^0.8.0;" in source
    assert 'import "forge-std/Test.sol";' in source
    assert "contract ReentrancyInClaimPoC is Test {" in source
    assert "function setUp() public {" in source
    assert "function test_exploit() public {" in source
    assert "Code4rena — Example" in source
    assert "Severity: high" in source
    assert 'import "../src/contracts/Vault.sol"' in source  # #L stripped
    assert "// vault.claim();" in source


def test_template_without_target_or_poc():
    source = poc_template(_finding(target="", poc=""), None)
    assert "engagement" in source
    assert "../src/" not in source
    assert "test_exploit" in source


def test_description_only_first_line():
    source = poc_template(_finding(), None)
    assert "State updated after external call." in source
    assert "Second line." not in source


def test_untrusted_fields_cannot_inject_solidity_lines():
    source = poc_template(
        _finding(
            title="Finding\ncontract Injected {}",
            target='Vault.sol\ncontract TargetInjected {}',
            description="Detail\ncontract DescriptionInjected {}",
            poc="call();\n}\ncontract PocInjected {}",
        ),
        {"name": "Contest\ncontract EngagementInjected {}"},
    )
    assert "\ncontract Injected" not in source
    assert "\ncontract TargetInjected" not in source
    assert "\ncontract DescriptionInjected" not in source
    assert "\ncontract EngagementInjected" not in source
    assert "\ncontract PocInjected" not in source
    assert "// contract PocInjected {}" in source
