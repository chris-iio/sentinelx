"""Tests for consented, bounded external audit analysis."""

import json

import pytest

from app.audit import agent
from app.audit.agent import MAX_FILES, analyze, generate_poc
from app.audit.poc import _contract_name


class FakePool:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, task, system, user):
        self.calls.append({"task": task, "system": system, "user": user})
        return self.response


def _files():
    return [{"path": "contracts/Vault.sol", "content": "contract Vault { }"}]


def _finding_json(**overrides):
    finding = {
        "title": "Reentrancy drains the vault",
        "severity": "critical",
        "target": "contracts/Vault.sol#L41",
        "description": "withdraw transfers before updating balances.",
        "impact": "All funds can be drained.",
        "remediation": "Update balances before the external call.",
    }
    finding.update(overrides)
    return finding


def _analyze(pool, **kwargs):
    return analyze(_files(), pool=pool, external_consent=True, **kwargs)


def test_external_consent_is_required_before_pool_call():
    pool = FakePool("[]")
    with pytest.raises(ValueError, match="consent"):
        analyze(_files(), pool=pool)
    with pytest.raises(ValueError, match="consent"):
        generate_poc(_files(), _finding_json(), pool=pool)
    assert pool.calls == []


def test_analyze_parses_only_strict_findings():
    pool = FakePool(json.dumps([_finding_json()]))
    result = _analyze(pool)
    assert result["dropped"] == 0
    assert result["parse_error"] is False
    assert result["findings"] == [_finding_json()]
    assert "raw" not in result
    assert len(result["response_sha256"]) == 64
    assert "hypothesis" in pool.calls[0]["system"]


def test_analyze_drops_items_that_fail_the_exact_contract():
    valid = _finding_json()
    items = [
        valid,
        {"severity": "high"},
        _finding_json(severity="catastrophic"),
        _finding_json(target="other.sol#L1"),
        {**valid, "extra": "not allowed"},
        "not-an-object",
    ]
    result = _analyze(FakePool(json.dumps(items)))
    assert result["findings"] == [valid]
    assert result["dropped"] == 5


def test_analyze_rejects_fences_trailing_text_and_large_output(monkeypatch):
    fenced = _analyze(FakePool("```json\n[]\n```"))
    assert fenced["findings"] == []
    assert fenced["parse_error"] is True

    trailing = _analyze(FakePool("[] trailing"))
    assert trailing["parse_error"] is True

    monkeypatch.setattr(agent, "MAX_MODEL_OUTPUT_BYTES", 2)
    with pytest.raises(ValueError, match="response exceeds"):
        _analyze(FakePool("[ ]"))


def test_raw_model_text_is_opt_in():
    raw = json.dumps([_finding_json()])
    hidden = _analyze(FakePool(raw))
    shown = _analyze(FakePool(raw), include_raw=True)
    assert "raw" not in hidden
    assert shown["raw"] == raw


def test_prior_memory_and_focus_are_bounded_and_private():
    pool = FakePool("[]")
    prior = [
        {
            "title": "Old issue",
            "status": "accepted",
            "analyst_note": "LOCAL SECRET NOTE",
            "description": "PRIVATE DESCRIPTION",
        }
    ]
    _analyze(pool, prior_findings=prior, focus="withdrawal paths")
    user = pool.calls[0]["user"]
    assert "[accepted] Old issue" in user
    assert "withdrawal paths" in user
    assert "LOCAL SECRET NOTE" not in user
    assert "PRIVATE DESCRIPTION" not in user

    with pytest.raises(ValueError, match="focus"):
        _analyze(FakePool("[]"), focus="x" * (agent.MAX_FOCUS_BYTES + 1))
    with pytest.raises(ValueError, match="title"):
        _analyze(FakePool("[]"), prior_findings=[{"title": 3, "status": "draft"}])
    with pytest.raises(ValueError, match="status"):
        _analyze(FakePool("[]"), prior_findings=[{"title": "x", "status": None}])


def test_file_records_reject_type_duplicate_absolute_and_traversal():
    invalid_scopes = [
        "not-a-list",
        [],
        [{"path": "Vault.sol", "content": b"bytes"}],
        [{"path": 7, "content": "x"}],
        [{"path": "/Vault.sol", "content": "x"}],
        [{"path": "../Vault.sol", "content": "x"}],
        [{"path": "a/./Vault.sol", "content": "x"}],
        [{"path": "a\\Vault.sol", "content": "x"}],
        [{"path": "Vault.sol", "content": "x", "secret": "value"}],
        [
            {"path": "Vault.sol", "content": "x"},
            {"path": "Vault.sol", "content": "y"},
        ],
    ]
    for scope in invalid_scopes:
        pool = FakePool("[]")
        with pytest.raises(ValueError):
            analyze(scope, pool=pool, external_consent=True)
        assert pool.calls == []


def test_file_count_individual_and_total_byte_limits(monkeypatch):
    too_many = [{"path": f"f{i}.sol", "content": "x"} for i in range(MAX_FILES + 1)]
    with pytest.raises(ValueError, match="files"):
        analyze(too_many, pool=FakePool("[]"), external_consent=True)

    monkeypatch.setattr(agent, "MAX_FILE_BYTES", 3)
    with pytest.raises(ValueError, match="file exceeds"):
        analyze(
            [{"path": "big.sol", "content": "éé"}],
            pool=FakePool("[]"),
            external_consent=True,
        )

    monkeypatch.setattr(agent, "MAX_FILE_BYTES", 10)
    monkeypatch.setattr(agent, "MAX_TOTAL_BYTES", 3)
    with pytest.raises(ValueError, match="scope"):
        analyze(
            [
                {"path": "a.sol", "content": "é"},
                {"path": "b.sol", "content": "é"},
            ],
            pool=FakePool("[]"),
            external_consent=True,
        )


def test_generate_poc_strips_exact_fence_and_names_contract():
    source = "// SPDX-License-Identifier: MIT\ncontract ReentrancyDrainsTheVaultPoC { }"
    pool = FakePool(f"```solidity\n{source}\n```")
    finding = _finding_json(analyst_note="DO NOT TRANSMIT")
    poc = generate_poc(
        _files(), finding, pool=pool, external_consent=True
    )
    assert poc["source"] == source
    assert poc["contract_name"] == _contract_name(finding["title"])
    assert len(poc["source_sha256"]) == 64
    assert pool.calls[0]["task"] == "poc"
    assert "Test skeleton to complete" in pool.calls[0]["user"]
    assert "DO NOT TRANSMIT" not in pool.calls[0]["user"]


def test_generate_poc_rejects_invalid_finding_and_output():
    pool = FakePool("contract XPoC { }")
    with pytest.raises(ValueError, match="severity"):
        generate_poc(
            _files(),
            _finding_json(severity="unknown"),
            pool=pool,
            external_consent=True,
        )
    assert pool.calls == []

    with pytest.raises(ValueError, match="strict Solidity"):
        generate_poc(
            _files(),
            _finding_json(),
            pool=FakePool("```json\n{}\n```"),
            external_consent=True,
        )


def test_generate_poc_accepts_bounded_unfenced_source():
    pool = FakePool("contract XPoC { }")
    poc = generate_poc(
        _files(), _finding_json(), pool=pool, external_consent=True
    )
    assert poc["source"] == "contract XPoC { }"
