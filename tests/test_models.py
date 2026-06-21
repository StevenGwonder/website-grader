import pytest
from datetime import datetime, timezone
from models import (
    AuditRun, SiteProfile, PageSnapshot, Evidence, Finding,
    Recommendation, ScoreSummary, MigrationResult, FindingStatus,
    migrate_legacy_report
)

def test_audit_run_defaults():
    run1 = AuditRun(target_url="https://example.com")
    run2 = AuditRun(target_url="https://example.com")
    
    assert run1.schema_version == "2.0.0"
    assert run1.audit_id != run2.audit_id  # UUIDs should be unique
    assert isinstance(run1.created_at, datetime)
    assert run1.created_at.tzinfo == timezone.utc

def test_site_profile_defaults():
    profile = SiteProfile(site_type="SaaS")
    assert isinstance(profile.locations, list)
    assert len(profile.locations) == 0
    # Modifying one profile list should not affect class/other profiles (non-mutable default test)
    profile.locations.append("US")
    
    profile2 = SiteProfile(site_type="Local Storefront")
    assert len(profile2.locations) == 0

def test_evidence_and_finding_defaults():
    ev = Evidence(
        type="css_selector",
        page_url="https://example.com",
        observed_value={"tag": "h1"},
        selector="h1"
    )
    assert isinstance(ev.captured_at, datetime)
    
    finding = Finding(
        check_id="test_check",
        category="Technical",
        status=FindingStatus.FAIL,
        severity="high",
        scope="page",
        title="Heading Test",
        observation="Missing headings",
        evidence=[ev]
    )
    assert finding.applicable is True
    assert finding.confidence == 1.0
    assert len(finding.evidence) == 1

def test_legacy_migration_serializer():
    legacy_payload = {
        "url": "https://seo.com",
        "score": {
            "overall_score": 53,
            "grade": "F"
        },
        "checks": [
            {
                "check_id": "tech_headings",
                "name": "Heading Hierarchy",
                "category": "Technical SEO",
                "severity": "high",
                "passed": False,
                "score": 0,
                "detail": "H1 count: 1, total headings: 68, skipped levels: True",
                "recommendation": "Use exactly one H1 per page."
            }
        ]
    }
    
    migrated = migrate_legacy_report(legacy_payload)
    assert isinstance(migrated, MigrationResult)
    assert migrated.schema_version == "2.0.0"
    assert migrated.audit_run.target_url == "https://seo.com"
    assert migrated.score_summary.overall_score == 53
    assert migrated.score_summary.health_score == 53.0
    assert len(migrated.findings) == 1
    
    finding = migrated.findings[0]
    assert finding.check_id == "tech_headings"
    assert finding.status == FindingStatus.FAIL
    assert len(finding.evidence) == 1
    assert finding.evidence[0].observed_value["detail"] == "H1 count: 1, total headings: 68, skipped levels: True"
    
    assert len(migrated.recommendations) == 1
    assert migrated.recommendations[0].validation_check_id == "tech_headings"
    assert migrated.recommendations[0].detail == "Use exactly one H1 per page."
