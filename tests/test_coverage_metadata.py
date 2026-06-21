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
    
    # Mock crawl_site, compute_score, generate_fixes, report_generation
    with patch("grader.crawl_site", return_value=crawl), \
         patch("grader._load_categories", return_value=[]), \
         patch("grader.compute_score", return_value={"overall_score": 100, "grade": "A"}), \
         patch("grader.generate_fixes", return_value=[]), \
         patch("report.generate_report", return_value="<html>Mock</html>"):

             
        # Mock sys.argv to specify a JSON output path
        json_file = tmp_path / "report.json"
        with patch.object(sys, 'argv', ["grader.py", "https://example.com", "--json", str(json_file)]):
            main()
            
        # Verify JSON content
        assert json_file.exists()
        with open(json_file) as f:
            data = json.load(f)
            
        assert "metadata" in data
        meta = data["metadata"]
        assert len(meta["discovered_urls"]) == 2
        assert meta["crawled_urls"] == ["https://example.com"]
        assert sorted(meta["excluded_urls"]) == ["https://example.com/a", "https://example.com/b"]
        assert meta["fetch_failures"] == {"https://example.com/fail": "HTTP 404"}
        assert meta["external_integrations"]["crux"] == "unavailable"
        assert meta["evaluated_checks_count"] == 0
        assert meta["unavailable_checks_count"] == 0
