"""Focused route and security tests for the Flask Audit workspace."""

import re

import pytest

from app import create_app
from app.audit.runner import RunResult


@pytest.fixture()
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SERVER_NAME": "localhost",
            "AUDIT_DB_PATH": str(tmp_path / "audit.db"),
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def _create_engagement(client, name="Example protocol", **overrides):
    values = {
        "name": name,
        "platform": "code4rena",
        "url": "https://example.test/program",
        "scope": "contracts at revision abc123",
        "prize_pool": "$50,000",
        "deadline": "2026-04-30",
    }
    values.update(overrides)
    response = client.post("/audit/engagements", data=values)
    assert response.status_code == 302
    return response.headers["Location"].rsplit("/", 1)[-1]


def _create_finding(client, engagement_id, title="Missing access control"):
    response = client.post(
        f"/audit/engagements/{engagement_id}/findings",
        data={
            "title": title,
            "severity": "high",
            "target": "contracts/Vault.sol#L42",
            "description": "Observed on revision abc123.",
            "impact": "Funds can be withdrawn.",
            "poc": "forge test --match-test test_claim",
            "remediation": "Require the owner and rerun the test.",
        },
    )
    assert response.status_code == 302
    return response.headers["Location"].rsplit("/", 1)[-1]


def test_primary_navigation_exposes_all_three_workspaces(client):
    body = client.get("/audit").get_data(as_text=True)
    assert 'href="/"' in body
    assert 'href="/audit"' in body
    assert 'href="/ctf"' in body
    assert ">Analyze<" in body
    assert ">Audit<" in body
    assert ">CTF<" in body


def test_engagement_create_detail_validation_and_escaping(client):
    engagement_id = _create_engagement(client, name="<script>alert(1)</script>")
    body = client.get(f"/audit/engagements/{engagement_id}").get_data(as_text=True)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "<script>alert(1)</script>" not in body
    assert "contracts at revision abc123" in body

    response = client.post(
        "/audit/engagements",
        data={"name": "Bad URL", "platform": "other", "url": "javascript:alert(1)"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/audit")

    response = client.post(
        "/audit/engagements",
        data={"name": "x" * 201, "platform": "other"},
    )
    assert response.status_code == 302
    assert len(client.application.audit_store.list_engagements()) == 1


def test_engagement_status_report_and_delete(client):
    engagement_id = _create_engagement(client)
    response = client.post(
        f"/audit/engagements/{engagement_id}/status", data={"status": "submitted"}
    )
    assert response.status_code == 302
    assert client.application.audit_store.get_engagement(engagement_id)["status"] == "submitted"

    response = client.post(
        f"/audit/engagements/{engagement_id}/status", data={"status": "invalid"}
    )
    assert response.status_code == 302
    assert client.application.audit_store.get_engagement(engagement_id)["status"] == "submitted"

    finding_id = _create_finding(client, engagement_id)
    report = client.get(f"/audit/engagements/{engagement_id}/report.md")
    assert report.status_code == 200
    assert report.mimetype == "text/markdown"
    assert "## [High] Missing access control" in report.get_data(as_text=True)
    assert "attachment" in report.headers["Content-Disposition"]

    client.post(f"/audit/findings/{finding_id}/delete")
    assert client.get(f"/audit/findings/{finding_id}").status_code == 404
    client.post(f"/audit/engagements/{engagement_id}/delete")
    assert client.get(f"/audit/engagements/{engagement_id}").status_code == 404


def test_finding_create_edit_status_and_truthful_workflow_copy(client):
    engagement_id = _create_engagement(client)
    finding_id = _create_finding(client, engagement_id, title="<img src=x onerror=alert(1)>")

    page = client.get(f"/audit/findings/{finding_id}")
    body = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "&lt;img src=x onerror=alert(1)&gt;" in body
    assert "<img src=x onerror=alert(1)>" not in body
    assert "not executed proof" in body
    assert "Reproducible run and recheck evidence" in body

    response = client.post(
        f"/audit/findings/{finding_id}/edit",
        data={
            "title": "Confirmed access control gap",
            "severity": "critical",
            "target": "contracts/Vault.sol#L42",
            "description": "Two independent traces confirm the claim.",
            "impact": "Full loss of funds.",
            "poc": "Run at abc123: PASS; rerun after fix: FAIL as expected.",
            "remediation": "Add authorization and retain the regression test.",
        },
    )
    assert response.status_code == 302
    finding = client.application.audit_store.get_finding(finding_id)
    assert finding["title"] == "Confirmed access control gap"
    assert finding["severity"] == "critical"

    client.post(f"/audit/findings/{finding_id}/status", data={"status": "accepted"})
    assert client.application.audit_store.get_finding(finding_id)["status"] == "accepted"
    client.post(f"/audit/findings/{finding_id}/status", data={"status": "trusted"})
    assert client.application.audit_store.get_finding(finding_id)["status"] == "accepted"


def test_scanner_intake_previews_before_importing_drafts(client):
    engagement_id = _create_engagement(client)
    text = (
        "[HIGH] Missing access control\n"
        "contracts/Vault.sol#L42\n"
        "[LOW] Unchecked dust amount\n"
    )
    preview = client.post(
        f"/audit/engagements/{engagement_id}/intake/preview", data={"text": text}
    )
    body = preview.get_data(as_text=True)
    assert preview.status_code == 200
    assert "Preview · 2 candidates" in body
    assert "Nothing has been imported" in body
    assert client.application.audit_store.list_findings(engagement_id) == []

    imported = client.post(
        f"/audit/engagements/{engagement_id}/intake/import", data={"text": text}
    )
    assert imported.status_code == 302
    findings = client.application.audit_store.list_findings(engagement_id)
    assert [finding["severity"] for finding in findings] == ["high", "low"]
    assert all(finding["status"] == "draft" for finding in findings)

    empty = client.post(
        f"/audit/engagements/{engagement_id}/intake/preview", data={"text": "  "}
    )
    assert empty.status_code == 302


def test_hardened_tool_run_previews_and_imports_exact_saved_output(
    client, monkeypatch
):
    engagement_id = _create_engagement(client)
    calls = []

    def fake_run(profile, target="", wordlist=""):
        calls.append((profile, target, wordlist))
        return RunResult(
            run_id="a" * 32,
            profile=profile,
            argv=("/usr/bin/slither", target, "--json", "-"),
            root="/work/audit",
            target=target,
            started_at="2026-03-20T10:00:00Z",
            ended_at="2026-03-20T10:00:01Z",
            exit_code=0,
            timed_out=False,
            truncated=False,
            output="[HIGH] <script>alert(1)</script>\ncontracts/Vault.sol#L42\n",
        )

    monkeypatch.setattr("app.routes.audit.runner.run_profile", fake_run)
    preview = client.post(
        f"/audit/engagements/{engagement_id}/run",
        data={"profile": "slither", "target": "/work/audit", "wordlist": ""},
    )
    body = preview.get_data(as_text=True)
    assert preview.status_code == 200
    assert "Executed run preview" in body
    assert "Complete within cap" in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "<script>alert(1)</script>" not in body
    assert calls == [("slither", "/work/audit", "")]
    assert client.application.audit_store.list_findings(engagement_id) == []

    imported = client.post(
        f"/audit/engagements/{engagement_id}/runs/{'a' * 32}/import"
    )
    assert imported.status_code == 302
    findings = client.application.audit_store.list_findings(engagement_id)
    assert len(findings) == 1
    assert findings[0]["status"] == "draft"
    assert calls == [("slither", "/work/audit", "")]

    client.post(f"/audit/engagements/{engagement_id}/runs/{'a' * 32}/import")
    assert len(client.application.audit_store.list_findings(engagement_id)) == 1


def test_audit_workspace_is_loopback_only(client):
    response = client.get(
        "/audit", environ_base={"REMOTE_ADDR": "203.0.113.10"}
    )
    assert response.status_code == 403

    engagement_id = _create_engagement(client)
    response = client.post(
        f"/audit/engagements/{engagement_id}/status",
        data={"status": "closed"},
        environ_base={"REMOTE_ADDR": "203.0.113.10"},
    )
    assert response.status_code == 403
    assert client.application.audit_store.get_engagement(engagement_id)["status"] == "active"


def test_audit_forms_require_csrf_and_accept_page_token(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": True,
            "SERVER_NAME": "localhost",
            "SECRET_KEY": "audit-csrf-test-key",
            "AUDIT_DB_PATH": str(tmp_path / "csrf-audit.db"),
        }
    )
    with app.test_client() as csrf_client:
        missing = csrf_client.post(
            "/audit/engagements", data={"name": "No token", "platform": "other"}
        )
        assert missing.status_code == 400
        assert app.audit_store.list_engagements() == []

        page = csrf_client.get("/audit").get_data(as_text=True)
        match = re.search(r'name="csrf_token" value="([^"]+)"', page)
        assert match is not None
        accepted = csrf_client.post(
            "/audit/engagements",
            data={
                "csrf_token": match.group(1),
                "name": "Protected engagement",
                "platform": "other",
            },
        )
        assert accepted.status_code == 302
        assert len(app.audit_store.list_engagements()) == 1
