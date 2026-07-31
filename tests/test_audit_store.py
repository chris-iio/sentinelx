"""Tests for the audit engagement store."""

from app.audit.store import AuditStore


def _store(tmp_path):
    return AuditStore(tmp_path / "audit.db")


def test_create_and_get_engagement(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(
        name="Code4rena — Example",
        platform="code4rena",
        url="https://code4rena.com/contests/example",
        prize_pool="$100,000",
        deadline="2026-08-01",
    )
    engagement = store.get_engagement(engagement_id)
    assert engagement is not None
    assert engagement["name"] == "Code4rena — Example"
    assert engagement["platform"] == "code4rena"
    assert engagement["status"] == "active"


def test_unknown_platform_falls_back_to_other(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="X", platform="nonsense")
    assert store.get_engagement(engagement_id)["platform"] == "other"


def test_list_engagements_includes_finding_counts(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="E")
    store.create_finding(engagement_id, title="F1", severity="high")
    store.create_finding(engagement_id, title="F2", severity="low")
    engagements = store.list_engagements()
    assert len(engagements) == 1
    assert engagements[0]["finding_count"] == 2


def test_set_engagement_status_validates(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="E")
    assert store.set_engagement_status(engagement_id, "submitted") is True
    assert store.set_engagement_status(engagement_id, "bogus") is False
    assert store.set_engagement_status("missing", "closed") is False


def test_create_finding_requires_engagement_and_valid_enums(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="E")
    assert store.create_finding("missing", title="F") is None
    assert store.create_finding(engagement_id, title="F", severity="bogus") is None
    assert store.create_finding(engagement_id, title="F", status="bogus") is None
    assert store.create_finding(engagement_id, title="F", severity="critical") is not None


def test_list_findings_orders_worst_severity_first(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="E")
    store.create_finding(engagement_id, title="low one", severity="low")
    store.create_finding(engagement_id, title="crit one", severity="critical")
    store.create_finding(engagement_id, title="med one", severity="medium")
    findings = store.list_findings(engagement_id)
    assert [f["severity"] for f in findings] == ["critical", "medium", "low"]


def test_list_findings_filters(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="E")
    store.create_finding(engagement_id, title="A", severity="high", status="draft")
    store.create_finding(engagement_id, title="B", severity="high", status="submitted")
    store.create_finding(engagement_id, title="C", severity="low", status="draft")
    assert len(store.list_findings(engagement_id, severity="high")) == 2
    assert len(store.list_findings(engagement_id, status="draft")) == 2
    assert len(store.list_findings(engagement_id, severity="high", status="draft")) == 1


def test_update_finding_applies_known_fields_only(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="E")
    finding_id = store.create_finding(engagement_id, title="F", severity="info")
    assert store.update_finding(
        finding_id, {"severity": "high", "status": "triaged", "nope": "x"}
    )
    finding = store.get_finding(finding_id)
    assert finding["severity"] == "high"
    assert finding["status"] == "triaged"
    assert "nope" not in finding
    assert store.update_finding(finding_id, {"severity": "bogus"})
    assert store.get_finding(finding_id)["severity"] == "high"
    assert store.update_finding("missing", {"severity": "high"}) is False


def test_delete_cascades_findings(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="E")
    finding_id = store.create_finding(engagement_id, title="F")
    assert store.delete_engagement(engagement_id) is True
    assert store.get_finding(finding_id) is None
    assert store.delete_engagement(engagement_id) is False


def test_engagement_stats(tmp_path):
    store = _store(tmp_path)
    engagement_id = store.create_engagement(name="E")
    store.create_finding(engagement_id, title="A", severity="critical", status="accepted")
    store.create_finding(engagement_id, title="B", severity="high")
    store.create_finding(engagement_id, title="C", severity="high")
    stats = store.engagement_stats(engagement_id)
    assert stats["total"] == 3
    assert stats["by_severity"]["high"] == 2
    assert stats["by_severity"]["critical"] == 1
    assert stats["by_status"]["accepted"] == 1
    assert stats["by_status"]["draft"] == 2
