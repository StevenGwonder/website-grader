import pytest
from crawler import CrawlResult, PageData
from checks.technical import TechnicalChecks
from models import FindingStatus

def test_evidence_populated_on_failure():
    # Make a crawler result where page has no canonical tag
    html = "<html><head><title>Test page</title></head><body><h1>No canonical here</h1></body></html>"
    page = PageData(url="https://example.com/blog/test", html=html, final_url="https://example.com/blog/test", status_code=200, ttfb_ms=10, headers={})
    
    crawl = CrawlResult(base_url="https://example.com")
    crawl.pages["https://example.com/blog/test"] = page
    
    checker = TechnicalChecks()
    result = checker._check_canonical(page)
    
    # Assert result failed and contains evidence
    assert result.status == FindingStatus.FAIL
    assert len(result.evidence) == 1
    
    ev = result.evidence[0]
    assert ev.page_url == "https://example.com/blog/test"
    assert ev.selector == "link[rel='canonical']"
    assert "detail" in ev.observed_value
    assert "No canonical tag found" in ev.observed_value["detail"]
