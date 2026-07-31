"""Tests for the audit_run CLI composition."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

from app.audit.store import AuditStore

SCRIPT = Path("tools/audit_run.py")


@pytest.fixture(autouse=True)
def audit_workspace_root(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_WORKSPACE_ROOTS", str(tmp_path))


@pytest.fixture()
def audit_run():
    spec = importlib.util.spec_from_file_location("audit_run_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakePool:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, task, system, user):
        self.calls.append({"task": task, "system": system, "user": user})
        return self.response


FINDING = {
    "title": "Reentrancy drains the vault",
    "severity": "critical",
    "target": "Vault.sol#L41",
    "description": "withdraw transfers before updating balances.",
    "impact": "All funds can be drained.",
    "remediation": "Update balances first.",
}


def _scope(tmp_path, *, foundry=False):
    (tmp_path / "Vault.sol").write_text("contract Vault { }", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not source", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.sol").write_text("vendored", encoding="utf-8")
    if foundry:
        (tmp_path / "foundry.toml").write_text("[profile.default]\n", encoding="utf-8")
    return tmp_path


def _store(tmp_path):
    return AuditStore(tmp_path / "audit.db")


def _verified_verdict(source):
    return {
        "status": "verified",
        "reason": "ok",
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "artifact_sha256": "a" * 64,
    }


def test_run_records_findings_without_forge(audit_run, tmp_path, capsys):
    _scope(tmp_path)
    store = _store(tmp_path)
    pool = FakePool(json.dumps([FINDING]))
    code = audit_run.main(
        ["--engagement", "treasury", "--path", str(tmp_path), "--consent-external"],
        pool=pool,
        store=store,
    )
    assert code == 0
    findings = store.list_findings(store.list_engagements()[0]["id"])
    assert len(findings) == 1
    assert findings[0]["status"] == "draft"
    assert findings[0]["severity"] == "critical"
    assert "Findings recorded: 1" in capsys.readouterr().out


def test_second_run_injects_prior_findings_as_memory(audit_run, tmp_path):
    _scope(tmp_path)
    store = _store(tmp_path)
    pool = FakePool(json.dumps([FINDING]))
    argv = ["--engagement", "treasury", "--path", str(tmp_path), "--consent-external"]
    assert audit_run.main(argv, pool=pool, store=store) == 0
    assert audit_run.main(argv, pool=pool, store=store) == 0
    second_prompt = pool.calls[1]["user"]
    assert "do not report these again" in second_prompt
    assert FINDING["title"] in second_prompt
    engagements = store.list_engagements()
    assert len(engagements) == 1


def test_strict_verified_finding_becomes_triaged(audit_run, tmp_path, monkeypatch):
    _scope(tmp_path, foundry=True)
    store = _store(tmp_path)
    pool = FakePool(json.dumps([FINDING]))
    monkeypatch.setattr(
        audit_run, "generate_poc",
        lambda files, finding, *, pool, external_consent=False: {"source": "contract XPoC { }", "contract_name": "XPoC"},
    )
    monkeypatch.setattr(
        audit_run,
        "verify_poc",
        lambda root, name, source: _verified_verdict(source),
    )
    assert audit_run.main(
        [
            "--engagement",
            "treasury",
            "--path",
            str(tmp_path),
            "--consent-external",
            "--strict",
        ],
        pool=pool,
        store=store,
    ) == 0
    finding = store.list_findings(store.list_engagements()[0]["id"])[0]
    assert finding["status"] == "triaged"
    assert finding["poc"] == "contract XPoC { }"


def test_unproven_finding_is_labeled_and_strict_suppresses(audit_run, tmp_path, monkeypatch):
    _scope(tmp_path, foundry=True)
    monkeypatch.setattr(
        audit_run, "generate_poc",
        lambda files, finding, *, pool, external_consent=False: {"source": "src", "contract_name": "XPoC"},
    )
    monkeypatch.setattr(
        audit_run, "verify_poc",
        lambda root, name, source: {"status": "unproven", "reason": "exploit test failed"},
    )

    store = _store(tmp_path)
    pool = FakePool(json.dumps([FINDING]))
    argv = ["--engagement", "treasury", "--path", str(tmp_path), "--consent-external"]
    assert audit_run.main(argv, pool=pool, store=store) == 0
    finding = store.list_findings(store.list_engagements()[0]["id"])[0]
    assert finding["status"] == "draft"
    assert "[verification: unproven" in finding["description"]

    strict_store = _store(tmp_path / "strict")
    assert audit_run.main(argv + ["--strict"], pool=FakePool(json.dumps([FINDING])),
                         store=strict_store) == 0
    engagement_id = strict_store.list_engagements()[0]["id"]
    assert strict_store.list_findings(engagement_id) == []


@pytest.mark.parametrize(
    ("foundry", "no_verify", "reason"),
    (
        (True, True, "explicitly skipped by --no-verify"),
        (False, False, "requires a Foundry project"),
    ),
)
def test_non_strict_unverified_scope_is_labeled(
    audit_run, tmp_path, foundry, no_verify, reason
):
    _scope(tmp_path, foundry=foundry)
    store = _store(tmp_path)
    argv = [
        "--engagement",
        "treasury",
        "--path",
        str(tmp_path),
        "--consent-external",
    ]
    if no_verify:
        argv.append("--no-verify")

    assert audit_run.main(
        argv, pool=FakePool(json.dumps([FINDING])), store=store
    ) == 0

    engagement_id = store.list_engagements()[0]["id"]
    finding = store.list_findings(engagement_id)[0]
    assert finding["status"] == "draft"
    assert "[verification: unverified" in finding["description"]
    assert reason in finding["description"]


def test_strict_no_verify_suppresses_finding(audit_run, tmp_path, monkeypatch):
    _scope(tmp_path, foundry=True)
    monkeypatch.setattr(
        audit_run,
        "verify_poc",
        lambda root, name, source: pytest.fail("verification must stay disabled"),
    )
    store = _store(tmp_path)
    code = audit_run.main(
        [
            "--engagement",
            "treasury",
            "--path",
            str(tmp_path),
            "--consent-external",
            "--no-verify",
            "--strict",
        ],
        pool=FakePool(json.dumps([FINDING])),
        store=store,
    )
    assert code == 0
    engagement_id = store.list_engagements()[0]["id"]
    assert store.list_findings(engagement_id) == []


def test_strict_non_foundry_scope_suppresses_finding(audit_run, tmp_path):
    _scope(tmp_path)
    store = _store(tmp_path)
    code = audit_run.main(
        [
            "--engagement",
            "treasury",
            "--path",
            str(tmp_path),
            "--consent-external",
            "--strict",
        ],
        pool=FakePool(json.dumps([FINDING])),
        store=store,
    )
    assert code == 0
    engagement_id = store.list_engagements()[0]["id"]
    assert store.list_findings(engagement_id) == []


def test_strict_rejects_verified_status_without_exact_artifact(
    audit_run, tmp_path, monkeypatch
):
    _scope(tmp_path, foundry=True)
    monkeypatch.setattr(
        audit_run,
        "generate_poc",
        lambda files, finding, *, pool, external_consent=False: {
            "source": "contract XPoC { }",
            "contract_name": "XPoC",
        },
    )
    monkeypatch.setattr(
        audit_run,
        "verify_poc",
        lambda root, name, source: {"status": "verified", "reason": "passed"},
    )
    store = _store(tmp_path)
    code = audit_run.main(
        [
            "--engagement",
            "treasury",
            "--path",
            str(tmp_path),
            "--consent-external",
            "--strict",
        ],
        pool=FakePool(json.dumps([FINDING])),
        store=store,
    )
    assert code == 0
    engagement_id = store.list_engagements()[0]["id"]
    assert store.list_findings(engagement_id) == []


def test_unverified_finding_is_labeled_and_strict_suppresses(
    audit_run, tmp_path, monkeypatch
):
    _scope(tmp_path, foundry=True)
    monkeypatch.setattr(
        audit_run,
        "generate_poc",
        lambda files, finding, *, pool, external_consent=False: {
            "source": "contract XPoC { }",
            "contract_name": "XPoC",
        },
    )
    monkeypatch.setattr(
        audit_run,
        "verify_poc",
        lambda root, name, source: {
            "status": "unverified",
            "reason": "isolation failed",
        },
    )
    argv = ["--engagement", "treasury", "--path", str(tmp_path), "--consent-external"]

    store = _store(tmp_path)
    assert audit_run.main(argv, pool=FakePool(json.dumps([FINDING])), store=store) == 0
    finding = store.list_findings(store.list_engagements()[0]["id"])[0]
    assert finding["status"] == "draft"
    assert "[verification: unverified" in finding["description"]

    strict_store = _store(tmp_path / "strict-unverified")
    assert audit_run.main(
        argv + ["--strict"],
        pool=FakePool(json.dumps([FINDING])),
        store=strict_store,
    ) == 0
    engagement_id = strict_store.list_engagements()[0]["id"]
    assert strict_store.list_findings(engagement_id) == []


def test_no_workspace_roots_fails_before_source_collection(
    audit_run, tmp_path, monkeypatch, capsys
):
    _scope(tmp_path)
    monkeypatch.delenv("AUDIT_WORKSPACE_ROOTS")
    monkeypatch.setattr(
        audit_run,
        "collect_files",
        lambda root: pytest.fail("source collection must not start"),
    )
    pool = FakePool(json.dumps([FINDING]))
    code = audit_run.main(
        ["--engagement", "treasury", "--path", str(tmp_path), "--consent-external"],
        pool=pool,
        store=_store(tmp_path),
    )
    assert code == 2
    assert "AUDIT_WORKSPACE_ROOTS" in capsys.readouterr().err
    assert pool.calls == []


def test_missing_or_malformed_workspace_roots_fail_closed(
    audit_run, tmp_path, monkeypatch, capsys
):
    _scope(tmp_path)
    for configured_roots in (
        str(tmp_path / "missing-root"),
        os.pathsep * 2,
        f"{tmp_path}{os.pathsep}{tmp_path / 'missing-root'}",
    ):
        monkeypatch.setenv("AUDIT_WORKSPACE_ROOTS", configured_roots)
        code = audit_run.main(
            ["--engagement", "treasury", "--path", str(tmp_path)],
            pool=FakePool("[]"),
            store=_store(tmp_path),
        )
        assert code == 2
        assert "AUDIT_WORKSPACE_ROOTS" in capsys.readouterr().err


def test_out_of_root_project_fails_before_source_collection(
    audit_run, tmp_path, monkeypatch, capsys
):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    project = tmp_path / "outside"
    project.mkdir()
    _scope(project)
    monkeypatch.setenv("AUDIT_WORKSPACE_ROOTS", str(allowed))
    monkeypatch.setattr(
        audit_run,
        "collect_files",
        lambda root: pytest.fail("source collection must not start"),
    )
    pool = FakePool(json.dumps([FINDING]))
    code = audit_run.main(
        ["--engagement", "treasury", "--path", str(project), "--consent-external"],
        pool=pool,
        store=_store(tmp_path),
    )
    assert code == 2
    assert "outside" in capsys.readouterr().err
    assert pool.calls == []


def test_project_symlink_escape_fails_before_source_collection(
    audit_run, tmp_path, monkeypatch, capsys
):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    _scope(outside)
    linked_project = allowed / "linked-project"
    linked_project.symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("AUDIT_WORKSPACE_ROOTS", str(allowed))
    monkeypatch.setattr(
        audit_run,
        "collect_files",
        lambda root: pytest.fail("source collection must not start"),
    )
    pool = FakePool(json.dumps([FINDING]))
    code = audit_run.main(
        [
            "--engagement",
            "treasury",
            "--path",
            str(linked_project),
            "--consent-external",
        ],
        pool=pool,
        store=_store(tmp_path),
    )
    assert code == 2
    assert "outside" in capsys.readouterr().err
    assert pool.calls == []


def test_source_symlink_is_not_read_or_transmitted(audit_run, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _scope(project)
    outside_source = tmp_path / "outside.sol"
    outside_source.write_text("DO NOT TRANSMIT", encoding="utf-8")
    (project / "Linked.sol").symlink_to(outside_source)
    pool = FakePool(json.dumps([FINDING]))

    code = audit_run.main(
        ["--engagement", "treasury", "--path", str(project), "--consent-external"],
        pool=pool,
        store=_store(tmp_path),
    )
    assert code == 0
    assert "DO NOT TRANSMIT" not in pool.calls[0]["user"]


def test_missing_directory_fails_the_run(audit_run, tmp_path, capsys):
    code = audit_run.main(
        ["--engagement", "treasury", "--path", str(tmp_path / "nope")],
        pool=FakePool("[]"),
        store=_store(tmp_path),
    )
    assert code == 2
    assert "does not exist" in capsys.readouterr().err


def test_empty_scope_fails_the_run(audit_run, tmp_path, capsys):
    (tmp_path / "notes.txt").write_text("no source here", encoding="utf-8")
    code = audit_run.main(
        ["--engagement", "treasury", "--path", str(tmp_path)],
        pool=FakePool("[]"),
        store=_store(tmp_path),
    )
    assert code == 2
    assert "no supported source files" in capsys.readouterr().err


def test_analysis_requires_consent_external(audit_run, tmp_path, capsys):
    _scope(tmp_path)
    pool = FakePool(json.dumps([FINDING]))
    code = audit_run.main(
        ["--engagement", "treasury", "--path", str(tmp_path)],
        pool=pool,
        store=_store(tmp_path),
    )
    assert code == 2
    assert "consent" in capsys.readouterr().err
    assert pool.calls == []


def test_json_summary(audit_run, tmp_path, capsys):
    _scope(tmp_path)
    pool = FakePool(json.dumps([FINDING, {"no": "title"}]))
    code = audit_run.main(
        ["--engagement", "treasury", "--path", str(tmp_path), "--consent-external", "--json"],
        pool=pool,
        store=_store(tmp_path),
    )
    assert code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["findings"] == 1
    assert summary["dropped_unparseable"] == 1
    assert summary["scope_files"] == 1
