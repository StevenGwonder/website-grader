import pytest
from checks.registry import get_rule_metadata, RULE_REGISTRY

def test_rule_registry_lookup():
    # Verify we can lookup some check IDs and get correct fields
    meta = get_rule_metadata("tech_meta_title")
    assert meta is not None
    assert meta.check_id == "tech_meta_title"
    assert meta.category == "Technical SEO"
    assert meta.default_severity == "high"
    assert "Title should be 30-60 chars" in meta.recommendation_template
    assert len(meta.documentation_references) > 0

    meta_nonexistent = get_rule_metadata("non_existent_check_id")
    assert meta_nonexistent is None

def test_registry_size():
    # Make sure we registered all 53 checks
    assert len(RULE_REGISTRY) == 58  # 53 original + 5 External Intelligence

def test_all_implemented_checks_registered():
    from checks import _load_categories
    from crawler import CrawlResult, PageData
    
    crawl = CrawlResult(base_url="https://example.com")
    page = PageData(url="https://example.com", html="<html><head><title>Test</title></head><body><h1>Test</h1></body></html>", final_url="https://example.com", status_code=200, ttfb_ms=10, headers={})
    crawl.pages["https://example.com"] = page
    
    for CheckClass in _load_categories():
        checker = CheckClass()
        results = checker.run(crawl)
        for r in results:
            assert r.check_id in RULE_REGISTRY, f"Check ID '{r.check_id}' from {CheckClass.__name__} is not in the rule registry!"

