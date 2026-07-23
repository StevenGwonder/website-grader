import pytest
from crawler import CrawlResult, PageData
from grader import main
import json
import sys
from unittest.mock import patch, MagicMock

def test_coverage_metadata_in_json(tmp_path):
    # Setup mock crawl result
    crawl = CrawlResult(base_url="https://example.com")
    crawl.discovered_urls = {"https://example.com/a", "https://example.com/b"}
    crawl.crawled_urls = {"https://example.com"}
    crawl.excluded_urls = {"https://example.com/a", "https://example.com/b"}
    crawl.fetch_failures = {"https://example.com/fail": "HTTP 404"}
    
    # Mock crawl_site, _load_categories, compute_score, generate_fixes, report_generation
    with patch("grader.crawl_site", return_value=crawl), \
         patch("grader._load_categories", return_value=[]), \
         patch("grader.compute_score", return_value={"overall_score": 100, "grade": "A", "categories": {}}), \
         patch("grader.generate_fixes", return_value={}), \
         patch("grader.generate_report", return_value="<html>Mock</html>"):

        # Mock sys.argv for CLI mode
        with patch.object(sys, 'argv', ["grader.py", "https://example.com"]):
            main()

    # Verify the report file was created
    import os
    from datetime import datetime
    domain = "example.com"
    timestamp = datetime.now().strftime("%Y-%m-%d")
    report_path = f"reports/{domain}-{timestamp}.html"
    assert os.path.exists(report_path)
    with open(report_path) as f:
        assert f.read() == "<html>Mock</html>"
