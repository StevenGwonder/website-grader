import pytest
from models import Finding, FindingStatus, Evidence
from scoring import deduplicate_findings
from datetime import datetime, timezone

def test_deduplicate_findings():
    # 1. Create duplicate layout findings on page1 and page2
    ev1 = Evidence(
        evidence_id="1",
        type="selector",
        page_url="https://example.com/page1",
        observed_value={"detail": "Missing alt text"},
        selector="footer img"
    )
    finding1 = Finding(
        finding_id="f1",
        check_id="alt_text",
        category="Accessibility",
        status=FindingStatus.FAIL,
        severity="high",
        scope="page",
        page_url="https://example.com/page1",
        title="Image Alt Text",
        observation="Images in footer are missing alt text",
        evidence=[ev1]
    )
    
    ev2 = Evidence(
        evidence_id="2",
        type="selector",
        page_url="https://example.com/page2",
        observed_value={"detail": "Missing alt text"},
        selector="footer img"
    )
    finding2 = Finding(
        finding_id="f2",
        check_id="alt_text",
        category="Accessibility",
        status=FindingStatus.FAIL,
        severity="high",
        scope="page",
        page_url="https://example.com/page2",
        title="Image Alt Text",
        observation="Images in footer are missing alt text",
        evidence=[ev2]
    )
    
    # 2. Run deduplication
    results = deduplicate_findings([finding1, finding2])
    
    # 3. Assertions
    assert len(results) == 1
    consolidated = results[0]
    assert consolidated.check_id == "alt_text"
    assert consolidated.scope == "site"
    assert "Found on 2 pages" in consolidated.observation
    assert len(consolidated.evidence) == 2
    
    urls = {ev.page_url for ev in consolidated.evidence}
    assert urls == {"https://example.com/page1", "https://example.com/page2"}
