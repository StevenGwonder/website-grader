import os
import pytest
from unittest.mock import patch

from crawler import crawl_site
from checks import _load_categories
from scoring import compute_score
from fixes import generate_fixes
from tests.fixtures.seo_com_frozen.helper import mock_network

def test_frozen_seo_com_audit():
    """Runs the full grading and scoring engine against the frozen seo.com fixture without live network."""
    
    # Enable the mock network context
    patches = mock_network()
    for p in patches:
        p.start()
        
    try:
        # 1. Crawl (should hit mock filesystem loader instead of live network)
        crawl_result = crawl_site("https://seo.com", max_pages=5)
        
        assert not crawl_result.error
        assert len(crawl_result.pages) == 5
        assert "https://seo.com" in crawl_result.pages
        assert crawl_result.robots_txt is not None
        assert "sitemap.xml" in crawl_result.robots_txt
        # The legacy parser reports 0 URLs due to the namespace parsing bug.
        assert len(crawl_result.sitemap_urls) == 0
        
        # 2. Run all diagnostic categories
        all_results = []
        for CheckClass in _load_categories():
            checker = CheckClass()
            results = checker.run(crawl_result)
            all_results.extend(results)
            
        assert len(all_results) > 0
        
        # 3. Compute score and verify it matches the legacy baseline
        score_data = compute_score(all_results)
        print("MOCK CATEGORY SCORES:", score_data)
        
        # Print failed checks to see what is failing differently
        for r in all_results:
            if not r.passed:
                print(f"FAILED CHECK: {r.check_id} | score={r.score} | detail={r.detail}")
                if r.check_id == "content_uniqueness":
                    print("UNIQUENESS DATA:", r.data)
        
        # The baseline score of seo.com under the legacy audit engine is 53
        assert score_data["overall_score"] == 53
        assert score_data["grade"] == "F"
        
        # Verify specific category scores match the legacy audit report
        categories = score_data["categories"]
        assert categories["Technical SEO"]["score"] == 62
        assert categories["Local SEO"]["score"] == 0
        assert categories["Performance"]["score"] == 82
        assert categories["Content Quality"]["score"] == 65
        assert categories["Security"]["score"] == 76
        assert categories["Accessibility"]["score"] == 33
        assert categories["Social & Conversion"]["score"] == 100
        
        # 4. Generate fixes and HTML report to confirm no exceptions are thrown
        fixes = generate_fixes(crawl_result, all_results)
        assert len(fixes) > 0
        
        try:
            from report import generate_report
            html_report = generate_report(crawl_result, all_results, score_data, fixes, "https://seo.com")
            assert len(html_report) > 0
            assert "Website Audit Dashboard" in html_report
        except ImportError:
            pass  # report.py not available
            
    finally:
        # Stop mock patches
        for p in patches:
            p.stop()
