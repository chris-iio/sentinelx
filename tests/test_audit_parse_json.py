"""Tests for JSON scanner intake parsing (Slither, osv-scanner, npm audit)."""

import json

from app.audit.parse import parse_intake


def _slither_output() -> str:
    return json.dumps(
        {
            "success": True,
            "results": {
                "detectors": [
                    {
                        "check": "reentrancy-eth",
                        "impact": "High",
                        "confidence": "Medium",
                        "description": "Reentrancy in Vault.claim() (contracts/Vault.sol#42)\n",
                        "elements": [
                            {
                                "type": "function",
                                "name": "claim",
                                "source_mapping": {
                                    "filename_relative": "contracts/Vault.sol",
                                    "lines": [42, 43, 44],
                                },
                            }
                        ],
                    },
                    {
                        "check": "naming-convention",
                        "impact": "Informational",
                        "description": "Variable _x is not in mixedCase\n",
                        "elements": [],
                    },
                ]
            },
        }
    )


def test_slither_json_maps_detectors():
    candidates = parse_intake(_slither_output())
    assert len(candidates) == 2
    first = candidates[0]
    assert first["severity"] == "high"
    assert first["title"] == "reentrancy eth"
    assert first["target"] == "contracts/Vault.sol#L42-44"
    assert "Reentrancy in Vault.claim()" in first["description"]
    assert candidates[1]["severity"] == "info"
    assert candidates[1]["target"] == ""


def _osv_output() -> str:
    return json.dumps(
        {
            "results": [
                {
                    "packages": [
                        {
                            "package": {"name": "lodash", "ecosystem": "npm"},
                            "installed_version": "4.17.20",
                            "vulnerabilities": [
                                {
                                    "id": "GHSA-xxxx-yyyy-zzzz",
                                    "aliases": ["CVE-2021-23337"],
                                    "summary": "Command injection in template",
                                    "severity": [
                                        {
                                            "type": "CVSS_V3",
                                            "score": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H",
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "package": {"name": "minimist", "ecosystem": "npm"},
                            "installed_version": "1.2.5",
                            "vulnerabilities": [
                                {
                                    "id": "GHSA-aaaa-bbbb-cccc",
                                    "summary": "Prototype pollution",
                                    "database_specific": {"severity": "LOW"},
                                }
                            ],
                        },
                    ]
                }
            ]
        }
    )


def test_osv_scanner_json_maps_vulnerabilities():
    candidates = parse_intake(_osv_output())
    assert len(candidates) == 2
    lodash = candidates[0]
    assert lodash["severity"] == "critical"
    assert "lodash@4.17.20" in lodash["title"]
    assert "CVE-2021-23337" in lodash["title"]
    assert lodash["target"] == "lodash"
    assert candidates[1]["severity"] == "low"


def _npm_audit_output() -> str:
    return json.dumps(
        {
            "vulnerabilities": {
                "axios": {
                    "severity": "high",
                    "range": "<1.7.4",
                    "via": [
                        {
                            "title": "Axios SSRF",
                            "url": "https://github.com/advisories/GHSA-1",
                        }
                    ],
                    "fixAvailable": True,
                },
                "leftpad": {"severity": "low", "via": ["transitive"], "fixAvailable": False},
            }
        }
    )


def test_npm_audit_json_maps_vulnerabilities():
    candidates = parse_intake(_npm_audit_output())
    assert len(candidates) == 2
    axios = candidates[0]
    assert axios["severity"] == "high"
    assert "axios" in axios["title"]
    assert "Affected range: <1.7.4" in axios["description"]
    assert "Axios SSRF" in axios["description"]
    assert "Fix available." in axios["description"]
    assert candidates[1]["severity"] == "low"


def test_unrecognized_json_falls_back_to_freeform():
    candidates = parse_intake('{"unrelated": true}')
    assert len(candidates) == 1
    assert candidates[0]["severity"] == "info"


def _semgrep_output() -> str:
    return json.dumps(
        {
            "results": [
                {
                    "check_id": "python.lang.security.audit.exec-use",
                    "path": "app/handler.py",
                    "start": {"line": 12},
                    "extra": {"severity": "ERROR", "message": "exec() used"},
                },
                {
                    "check_id": "generic.warnings.todo",
                    "path": "README.md",
                    "start": {"line": 3},
                    "extra": {"severity": "WARNING", "message": "TODO left"},
                },
            ]
        }
    )


def test_semgrep_json_maps_results():
    candidates = parse_intake(_semgrep_output())
    assert len(candidates) == 2
    first = candidates[0]
    assert first["severity"] == "high"
    assert first["title"] == "exec-use"
    assert first["target"] == "app/handler.py#L12"
    assert first["description"] == "exec() used"
    assert candidates[1]["severity"] == "medium"


def _mythril_output() -> str:
    return json.dumps(
        {
            "issues": [
                {
                    "swcID": "SWC-107",
                    "title": "Reentrancy",
                    "severity": "High",
                    "description": "External call before state update.",
                    "locations": [
                        {"sourceMap": {"filename": "Vault.sol", "lineno": 42}}
                    ],
                },
                {
                    "swcID": "SWC-104",
                    "title": "Unchecked Call Return Value",
                    "severity": "Medium",
                    "description": "Return value not checked.",
                    "locations": [],
                },
            ]
        }
    )


def test_mythril_json_maps_issues():
    candidates = parse_intake(_mythril_output())
    assert len(candidates) == 2
    first = candidates[0]
    assert first["severity"] == "high"
    assert first["title"] == "Reentrancy"
    assert first["target"] == "Vault.sol#L42"
    assert "SWC-107" in first["description"]
    assert candidates[1]["severity"] == "medium"
    assert candidates[1]["target"] == ""


def test_json_embedded_in_log_noise_is_parsed():
    noisy = (
        "INFO:Slither:compiling contracts\n"
        + _slither_output()
        + '\nWARN: something on stderr\n'
    )
    candidates = parse_intake(noisy)
    assert len(candidates) == 2
    assert candidates[0]["severity"] == "high"
    assert candidates[0]["source"] == "scanner"


def test_candidates_carry_source_markers():
    assert parse_intake(_slither_output())[0]["source"] == "scanner"
    assert parse_intake("[HIGH] Still works\n")[0]["source"] == "lines"
    assert parse_intake("random notes")[0]["source"] == "freeform"


def test_text_input_still_uses_line_parsing():
    candidates = parse_intake("[HIGH] Still works\n")
    assert len(candidates) == 1
    assert candidates[0]["severity"] == "high"


def test_recognized_scanner_json_with_zero_findings_is_empty():
    outputs = [
        {"results": {"detectors": []}},
        {"results": []},
        {"vulnerabilities": {}},
        {"issues": []},
    ]
    for output in outputs:
        assert parse_intake(json.dumps(output)) == []
