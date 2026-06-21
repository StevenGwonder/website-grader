import pytest
import gzip
import hashlib
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

from crawler import (
    normalize_url,
    RobotsParser,
    _parse_sitemap_xml,
    _fetch_and_parse_sitemap,
    _fetch_page,
    crawl_site,
    CrawlResult,
    PageData,
    compare_raw_vs_rendered
)
from checks.technical import TechnicalChecks, classify_link_outcome

def test_url_normalization():
    # Lowercase host, strip default ports, strip fragments, duplicate trailing slashes, track params
    assert normalize_url("http://EXAMPLE.COM:80/path//?utm_source=123&gclid=abc#frag") == "http://example.com/path/"
    assert normalize_url("https://example.com:443/") == "https://example.com/"
    assert normalize_url("https://example.com/path//sub//") == "https://example.com/path//sub/"
    assert normalize_url("example.com") == "https://example.com"

def test_robots_parser():
    content = """
    User-agent: GPTBot
    Disallow: /private/
    
    User-agent: *
    Disallow: /wp-admin/
    Allow: /wp-admin/admin-ajax.php
    """
    parser = RobotsParser(content)
    # GPTBot
    assert not parser.can_fetch("GPTBot", "https://example.com/private/page")
    assert parser.can_fetch("GPTBot", "https://example.com/public/page")
    # General Bot
    assert not parser.can_fetch("Googlebot", "https://example.com/wp-admin/index.php")
    assert parser.can_fetch("Googlebot", "https://example.com/wp-admin/admin-ajax.php")
    assert parser.can_fetch("Googlebot", "https://example.com/")

def test_recursive_sitemap_parsing():
    sitemap_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
       <sitemap>
          <loc>https://example.com/child-sitemap.xml</loc>
       </sitemap>
    </sitemapindex>"""
    
    child_sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
       <url>
          <loc>https://example.com/page1</loc>
       </url>
    </urlset>"""
    
    result = CrawlResult(base_url="https://example.com")
    crawled_sitemaps = set()
    
    session = MagicMock()
    mock_resp = MagicMock(status_code=200, content=child_sitemap_xml.encode('utf-8'))
    session.get.return_value = mock_resp
    
    _parse_sitemap_xml(sitemap_index_xml.encode('utf-8'), "https://example.com/sitemap.xml", 5, session, result, crawled_sitemaps)
    
    assert "https://example.com/page1" in result.sitemap_urls
    session.get.assert_called_once_with("https://example.com/child-sitemap.xml", timeout=5)

def test_redirect_tracing():
    # 1 hop redirect
    mock_resp1 = MagicMock(status_code=301, headers={"Location": "https://example.com/target"})
    mock_resp2 = MagicMock(status_code=200, headers={}, content=b"target page")
    
    session = MagicMock()
    session.get.side_effect = [mock_resp1, mock_resp2]
    
    page = _fetch_page("https://example.com/source", session=session)
    assert page.redirect_type == "redirect"
    assert len(page.redirect_hops) == 2
    assert page.redirect_hops[0]["status_code"] == 301
    assert page.redirect_hops[1]["status_code"] == 200
    
    # Redirect chain (> 1 hop)
    session = MagicMock()
    mock_r1 = MagicMock(status_code=302, headers={"Location": "https://example.com/hop2"})
    mock_r2 = MagicMock(status_code=301, headers={"Location": "https://example.com/target"})
    mock_r3 = MagicMock(status_code=200, headers={}, content=b"final")
    session.get.side_effect = [mock_r1, mock_r2, mock_r3]
    
    page = _fetch_page("https://example.com/source", session=session)
    assert page.redirect_type == "redirect_chain"
    assert len(page.redirect_hops) == 3

def test_external_link_outcome_classification():
    assert classify_link_outcome(403, None) == "access_restricted"
    assert classify_link_outcome(429, None) == "rate_limited"
    assert classify_link_outcome(None, "Connection timed out") == "timeout"
    assert classify_link_outcome(None, "Could not resolve host") == "dns_error"
    assert classify_link_outcome(None, "SSL handshake failed") == "tls_failure"
    assert classify_link_outcome(200, None) == "valid"

def test_raw_vs_rendered_comparison():
    raw_html = """<html><head>
    <title>Raw Title</title>
    <link rel="canonical" href="https://example.com/raw">
    <meta name="robots" content="index, follow">
    </head><body>
    <h1>Heading 1</h1>
    <p>Some words here</p>
    </body></html>"""
    
    rendered_html = """<html><head>
    <title>Rendered Title</title>
    <link rel="canonical" href="https://example.com/rendered">
    <meta name="robots" content="noindex, follow">
    </head><body>
    <h1>Heading 1</h1>
    <h2>Heading 2</h2>
    <p>Some words here that are different and longer</p>
    <script type="application/ld+json">{"@type":"Product","name":"A Product"}</script>
    </body></html>"""
    
    page = PageData(
        url="https://example.com",
        html=raw_html,
        final_url="https://example.com",
        status_code=200,
        ttfb_ms=50.0,
        headers={}
    )
    page.rendered_html = rendered_html
    disparities = compare_raw_vs_rendered(page)
    
    assert "title" in disparities
    assert disparities["title"]["raw"] == "Raw Title"
    assert disparities["title"]["rendered"] == "Rendered Title"
    
    assert "canonical" in disparities
    assert disparities["canonical"]["raw"] == "https://example.com/raw"
    assert disparities["canonical"]["rendered"] == "https://example.com/rendered"
    
    assert "robots" in disparities
    assert disparities["robots"]["raw"] == "index, follow"
    assert disparities["robots"]["rendered"] == "noindex, follow"
    
    assert "headings" in disparities
    assert disparities["headings"]["raw"] == ["h1"]
    assert disparities["headings"]["rendered"] == ["h1", "h2"]
    
    assert "word_count" in disparities
    assert disparities["word_count"]["raw"] == 5
    assert disparities["word_count"]["rendered"] == 12
    
    assert "structured_data" in disparities
    assert disparities["structured_data"]["raw"] == []
    assert disparities["structured_data"]["rendered"] == ["Product"]

def test_static_page_snapshots_hashing():
    raw_html = "<html><body>Test</body></html>"
    mock_resp = MagicMock(status_code=200, content=raw_html.encode('utf-8'))
    session = MagicMock()
    session.get.return_value = mock_resp
    
    page = _fetch_page("https://example.com", session=session)
    assert page.content_hash == hashlib.sha256(raw_html.encode('utf-8')).hexdigest()
    assert page.raw_content == raw_html.encode('utf-8')
