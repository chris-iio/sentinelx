"""Tests for the audit workbench REST API (/api/audit/*)."""

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SERVER_NAME": "localhost",
            "AUDIT_DB_PATH": str(tmp_path / "audit.db"),
        }
    )
    return app.test_client()


def test_mutating_audit_api_requires_csrf_even_from_loopback(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": True,
            "SERVER_NAME": "localhost",
            "AUDIT_DB_PATH": str(tmp_path / "audit-csrf.db"),
        }
    )
    protected_client = app.test_client()

    assert protected_client.get("/api/audit/meta").status_code == 200
    response = protected_client.post("/api/audit/engagements", json={"name": "Example"})

    assert response.status_code == 400
    assert b"CSRF token is missing" in response.data


def _create_engagement(client, **overrides):
    payload = {"name": "Code4rena — Example", "platform": "code4rena"}
    payload.update(overrides)
    response = client.post("/api/audit/engagements", json=payload)
    assert response.status_code == 201
    return response.get_json()["engagement"]


def test_meta_returns_enums(client):
    data = client.get("/api/audit/meta").get_json()
    assert "code4rena" in data["platforms"]
    assert "immunefi" in data["platforms"]
    assert "critical" in data["severities"]
    assert "accepted" in data["finding_statuses"]


def test_create_engagement_requires_json_and_name(client):
    assert client.post("/api/audit/engagements").status_code == 400
    assert client.post("/api/audit/engagements", json={}).status_code == 400
    response = client.post("/api/audit/engagements", json={"name": "  "})
    assert response.status_code == 400


def test_api_rejects_wrong_field_types_and_oversized_values(client):
    assert client.post(
        "/api/audit/engagements", json={"name": 7}
    ).status_code == 400
    assert client.post(
        "/api/audit/engagements", json={"name": "x" * 201}
    ).status_code == 400
    engagement = _create_engagement(client)
    engagement_id = engagement["id"]
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/findings",
        json={"title": ["not", "text"]},
    ).status_code == 400
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/intake",
        json={"text": "[HIGH] x", "create": "yes"},
    ).status_code == 400
    assert client.patch(
        "/api/audit/findings/missing", json={"description": {"bad": True}}
    ).status_code == 400
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/run",
        json={"profile": ["strings"]},
    ).status_code == 400


def test_engagement_crud_round_trip(client):
    engagement = _create_engagement(client, url="https://example.test")
    engagement_id = engagement["id"]

    listed = client.get("/api/audit/engagements").get_json()["engagements"]
    assert [e["id"] for e in listed] == [engagement_id]

    fetched = client.get(f"/api/audit/engagements/{engagement_id}").get_json()
    assert fetched["engagement"]["stats"]["total"] == 0

    updated = client.patch(
        f"/api/audit/engagements/{engagement_id}", json={"status": "submitted"}
    )
    assert updated.get_json()["engagement"]["status"] == "submitted"
    assert client.patch(
        f"/api/audit/engagements/{engagement_id}", json={"status": "bogus"}
    ).status_code == 400

    assert client.delete(f"/api/audit/engagements/{engagement_id}").status_code == 200
    assert client.get(f"/api/audit/engagements/{engagement_id}").status_code == 404


def test_missing_engagement_404(client):
    assert client.get("/api/audit/engagements/nope").status_code == 404
    assert client.delete("/api/audit/engagements/nope").status_code == 404
    assert client.get("/api/audit/engagements/nope/findings").status_code == 404


def test_finding_crud_and_filters(client):
    engagement = _create_engagement(client)
    engagement_id = engagement["id"]

    assert client.post(
        f"/api/audit/engagements/{engagement_id}/findings", json={}
    ).status_code == 400
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/findings",
        json={"title": "X", "severity": "bogus"},
    ).status_code == 400

    created = client.post(
        f"/api/audit/engagements/{engagement_id}/findings",
        json={"title": "Reentrancy", "severity": "high", "target": "Vault.sol#L1"},
    )
    assert created.status_code == 201
    finding_id = created.get_json()["finding"]["id"]

    listed = client.get(
        f"/api/audit/engagements/{engagement_id}/findings?severity=high"
    ).get_json()
    assert len(listed["findings"]) == 1
    assert listed["stats"]["by_severity"]["high"] == 1
    assert client.get(
        f"/api/audit/engagements/{engagement_id}/findings?severity=bogus"
    ).status_code == 400

    updated = client.patch(
        f"/api/audit/findings/{finding_id}", json={"status": "accepted"}
    )
    assert updated.get_json()["finding"]["status"] == "accepted"

    assert client.delete(f"/api/audit/findings/{finding_id}").status_code == 200
    assert client.get(f"/api/audit/findings/{finding_id}").status_code == 404


def test_intake_preview_and_create(client):
    engagement = _create_engagement(client)
    engagement_id = engagement["id"]
    text = "[HIGH] Missing access control\ncontracts/Vault.sol#L10\n[LOW] Dust amounts\n"

    preview = client.post(
        f"/api/audit/engagements/{engagement_id}/intake", json={"text": text}
    )
    assert preview.status_code == 200
    body = preview.get_json()
    assert body["created"] == 0
    assert len(body["candidates"]) == 2
    assert client.get(
        f"/api/audit/engagements/{engagement_id}/findings"
    ).get_json()["findings"] == []

    created = client.post(
        f"/api/audit/engagements/{engagement_id}/intake",
        json={"text": text, "create": True},
    )
    assert created.status_code == 201
    assert created.get_json()["created"] == 2
    findings = client.get(
        f"/api/audit/engagements/{engagement_id}/findings"
    ).get_json()["findings"]
    assert [f["severity"] for f in findings] == ["high", "low"]
    assert findings[0]["target"] == "contracts/Vault.sol#L10"


def test_intake_requires_text(client):
    engagement = _create_engagement(client)
    response = client.post(
        f"/api/audit/engagements/{engagement['id']}/intake", json={"text": "  "}
    )
    assert response.status_code == 400


def test_finding_poc_download(client):
    engagement = _create_engagement(client)
    engagement_id = engagement["id"]
    created = client.post(
        f"/api/audit/engagements/{engagement_id}/findings",
        json={
            "title": "Reentrancy in claim",
            "severity": "high",
            "target": "contracts/Vault.sol#L42",
        },
    )
    finding_id = created.get_json()["finding"]["id"]
    response = client.get(f"/api/audit/findings/{finding_id}/poc.sol")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "contract ReentrancyInClaimPoC is Test {" in body
    assert "test_exploit" in body
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.headers["Content-Disposition"].endswith('.t.sol"')
    assert client.get("/api/audit/findings/nope/poc.sol").status_code == 404


def test_tools_listing(client, monkeypatch):
    monkeypatch.delenv("AUDIT_WORKSPACE_ROOTS", raising=False)
    data = client.get("/api/audit/tools").get_json()
    names = [t["name"] for t in data["tools"]]
    for expected in ("slither", "semgrep", "osv-scanner", "npm-audit", "forge-test", "nmap-quick"):
        assert expected in names
    assert all("installed" in t for t in data["tools"])
    assert data["workspace_roots"] == []
    assert data["execution_enabled"] is False


def test_run_tool_executes_and_imports(client, tmp_path, monkeypatch):
    import os
    import stat

    monkeypatch.setenv("AUDIT_WORKSPACE_ROOTS", str(tmp_path))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "slither"
    counter = tmp_path / "executions"
    script.write_text(
        "#!/bin/sh\n"
        f"echo run >> '{counter}'\n"
        "echo '{\"results\":{\"detectors\":[{\"check\":\"reentrancy-eth\","
        "\"impact\":\"High\",\"description\":\"Reentrancy\",\"elements\":[]}]}}'\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    engagement = _create_engagement(client)
    engagement_id = engagement["id"]
    target = tmp_path / "contracts"
    target.mkdir()

    response = client.post(
        f"/api/audit/engagements/{engagement_id}/run",
        json={"profile": "slither", "target": str(target)},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["exit_code"] == 0
    assert body["exit_status"] == "exited"
    assert body["created"] == 0
    assert body["imported"] is False
    assert body["profile"] == "slither"
    assert body["tool"] == "slither"
    assert body["root"] == str(tmp_path)
    assert body["target"] == str(target)
    assert body["started_at"].endswith("Z")
    assert body["ended_at"].endswith("Z")
    assert body["timed_out"] is False
    assert body["truncated"] is False
    assert len(body["output_sha256"]) == 64
    assert len(body["candidates"]) == 1

    response = client.post(
        f"/api/audit/engagements/{engagement_id}/runs/{body['run_id']}/import",
        json={},
    )
    imported = response.get_json()
    assert response.status_code == 201
    assert imported["created"] == 1
    assert imported["imported"] is True
    assert imported["output"] == body["output"]
    assert imported["output_sha256"] == body["output_sha256"]
    assert counter.read_text().splitlines() == ["run"]
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/runs/{body['run_id']}/import",
        json={},
    ).status_code == 409
    findings = client.get(
        f"/api/audit/engagements/{engagement_id}/findings"
    ).get_json()["findings"]
    assert findings[0]["severity"] == "high"


def test_run_tool_validation(client, tmp_path, monkeypatch):
    monkeypatch.delenv("AUDIT_WORKSPACE_ROOTS", raising=False)
    engagement = _create_engagement(client)
    assert client.post(
        f"/api/audit/engagements/{engagement['id']}/run",
        json={"profile": "solc-version"},
    ).status_code == 400

    monkeypatch.setenv("AUDIT_WORKSPACE_ROOTS", str(tmp_path))
    engagement_id = engagement["id"]
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/run", json={}
    ).status_code == 400
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/run",
        json={"profile": "nope"},
    ).status_code == 400
    assert client.post(
        "/api/audit/engagements/nope/run",
        json={"profile": "slither", "target": str(tmp_path)},
    ).status_code == 404
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/run",
        json={"profile": "slither", "target": "/etc"},
    ).status_code == 400
    assert client.post(
        f"/api/audit/engagements/{engagement_id}/run",
        json={"profile": "strings", "target": str(tmp_path), "import": True},
    ).status_code == 400


def test_run_tool_freeform_output_is_not_imported(client, tmp_path, monkeypatch):
    import os
    import stat

    monkeypatch.setenv("AUDIT_WORKSPACE_ROOTS", str(tmp_path))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "strings"
    script.write_text("#!/bin/sh\necho 'plain unstructured output'\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    engagement = _create_engagement(client)
    engagement_id = engagement["id"]
    target = tmp_path / "f.bin"
    target.write_bytes(b"x")

    response = client.post(
        f"/api/audit/engagements/{engagement_id}/run",
        json={"profile": "strings", "target": str(target)},
    )
    body = response.get_json()
    assert body["candidates"][0]["source"] == "freeform"
    imported = client.post(
        f"/api/audit/engagements/{engagement_id}/runs/{body['run_id']}/import",
        json={},
    )
    assert imported.get_json()["created"] == 0
    assert client.get(
        f"/api/audit/engagements/{engagement_id}/findings"
    ).get_json()["findings"] == []


def test_report_markdown_download(client):
    engagement = _create_engagement(client)
    engagement_id = engagement["id"]
    client.post(
        f"/api/audit/engagements/{engagement_id}/findings",
        json={"title": "Reentrancy", "severity": "high", "impact": "Drain"},
    )
    response = client.get(f"/api/audit/engagements/{engagement_id}/report.md")
    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    body = response.get_data(as_text=True)
    assert "# Code4rena — Example — Security Review" in body
    assert "## [High] Reentrancy" in body
    assert "attachment" in response.headers["Content-Disposition"]
    assert client.get("/api/audit/engagements/nope/report.md").status_code == 404
