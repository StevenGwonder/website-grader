import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from crawler import CrawlResult, PageData
from checks.technical import TechnicalChecks
from checks.local_seo import LocalSeoChecks
from checks.content import ContentChecks
from checks.accessibility import AccessibilityChecks

def make_crawl_result(html, url="https://example.com"):
    page = PageData(url=url, html=html, final_url=url, status_code=200, ttfb_ms=100, headers={})
    result = CrawlResult(base_url=url)
    result.pages[url] = page
    return result

# 1. Sitemap index or invalid sitemap endpoint reported as "0 URLs"
def test_defect_sitemap_index_classification():
    sitemap_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
       <sitemap>
          <loc>http://www.example.com/sitemap1.xml.gz</loc>
       </sitemap>
    </sitemapindex>"""
    crawl = CrawlResult(base_url="https://example.com")
    crawl.sitemap_xml = sitemap_index_xml
    # Under current code, len(crawl.sitemap_urls) is 0 because it doesn't parse sitemapindex locs
    checker = TechnicalChecks()
    result = checker._check_sitemap(crawl)
    # Correct expected behavior: should be classified as a valid sitemap index, passed=True
    assert result.passed
    assert "index" in result.detail.lower()

# 2. External 403 Forbidden classified as a broken link instead of access-restricted or unverified
@patch("checks.technical.req.head")
def test_defect_external_403_classification(mock_head):
    mock_head.return_value = MagicMock(status_code=403)
    html = '<a href="https://g2.com/restricted-page">G2 Page</a>'
    crawl = make_crawl_result(html)
    checker = TechnicalChecks()
    result = checker._check_broken_links(crawl)
    # Correct expected behavior: not marked as a hard broken link
    assert result.passed
    assert len(result.data.get("broken_links", [])) == 0

# 3. A single-hop redirect classified as a redirect chain
def test_defect_single_hop_redirect_chain():
    crawl = CrawlResult(base_url="https://example.com")
    # Simulate single-hop redirects (e.g. HTTP to HTTPS or trailing slash)
    crawl.pages["https://example.com"] = PageData(
        url="https://example.com", html="", final_url="https://www.example.com/", status_code=200, ttfb_ms=100, headers={}
    )
    checker = TechnicalChecks()
    result = checker._check_redirect_chains(crawl)
    # Correct expected behavior: single redirects are not chains, should pass
    assert result.passed

# 4. Business name extracted solely from the <title> tag, creating false NAP mismatch
@pytest.mark.xfail(reason="ponytail: business name extracted solely from title tag falls back to keyword-stuffed SEO titles")
def test_defect_business_name_extraction_false_nap():
    html = """<html>
    <head><title>#1 Plumbing Services in Murrieta CA | Leak Repair Specialists</title></head>
    <body><h1>Best Plumbing</h1></body>
    </html>"""
    page = PageData(url="https://example.com", html=html, final_url="https://example.com", status_code=200, ttfb_ms=100, headers={})
    checker = LocalSeoChecks()
    nap = checker._extract_nap(page)
    # Correct expected behavior: should extract "Best Plumbing" from header or schema instead of keyword title
    assert nap["name"] == "Best Plumbing"

# 5. National, SaaS, ecommerce, or non-local website penalized with Local SEO zero
@pytest.mark.xfail(reason="ponytail: local checks run unconditionally on national/SaaS sites penalizing overall health")
def test_defect_site_type_applicability():
    # Simulate a SaaS site
    html = "<html><head><title>SaaS Platform</title></head><body><h1>Enterprise SaaS</h1></body></html>"
    crawl = make_crawl_result(html)
    # Correct expected behavior: local SEO checks should be skipped or marked NOT_APPLICABLE for SaaS
    checker = LocalSeoChecks()
    results = checker.run(crawl)
    for r in results:
        assert not r.passed or r.detail == "NOT_APPLICABLE" or r.score == 100

# 6. Obsolete FAQ schema advice presented as a Google rich-result opportunity
@pytest.mark.xfail(reason="ponytail: FAQ schema recommendation is obsolete and shouldn't be advised as rich-result opportunity")
def test_defect_obsolete_faq_advice():
    html = "<html><body><h1>No FAQ</h1></body></html>"
    crawl = make_crawl_result(html)
    checker = ContentChecks()
    result = checker._check_faq(crawl.homepage)
    # Correct expected behavior: should not recommend adding FAQ schema as a high-value opportunity
    assert "FAQPage" not in result.recommendation

# 7. Structured-data audit counts JSON-LD script blocks instead of parsing entities
@pytest.mark.xfail(reason="ponytail: structured data check counts script tags instead of validating entities")
def test_defect_structured_data_block_count():
    invalid_schema_html = """<html>
    <head>
        <script type="application/ld+json">{"invalid_json": true}</script>
    </head>
    </html>"""
    crawl = make_crawl_result(invalid_schema_html)
    checker = TechnicalChecks()
    result = checker._check_schema(crawl.homepage)
    # Correct expected behavior: should fail structured data validation due to invalid schema
    assert not result.passed

# 8. Keyword-density rule flags repetition without excluding boilerplate, nav, or footer
@pytest.mark.xfail(reason="ponytail: keyword density is calculated on raw text including navigation headers and footer boilerplate")
def test_defect_keyword_density_boilerplate():
    html = """<html>
    <body>
        <nav>Product Product Product Product Product Product Product Product Product Product Product Product</nav>
        <main>We build quality tools for your business.</main>
        <footer>Product Product Product Product Product Product Product Product Product Product Product Product</footer>
    </body>
    </html>"""
    page = PageData(url="https://example.com", html=html, final_url="https://example.com", status_code=200, ttfb_ms=100, headers={})
    checker = ContentChecks()
    result = checker._check_keyword_density(page)
    # Correct expected behavior: should pass because keywords in nav/footer are boilerplate
    assert result.passed

# 9. Readability score treated as a failure without page-type, audience, or industry context
@pytest.mark.xfail(reason="ponytail: readability is flagged as failure on technical docs without considering page classification")
def test_defect_readability_failure_context():
    # Technical/scientific B2B documentation which naturally has low readability score
    technical_html = """<html>
    <body>
        <p>The thermodynamic equilibrium of this chemical solution is determined by the stoichiometric ratio of reactants.</p>
    </body>
    </html>"""
    page = PageData(url="https://example.com", html=technical_html, final_url="https://example.com", status_code=200, ttfb_ms=100, headers={})
    checker = ContentChecks()
    result = checker._check_readability(page)
    # Correct expected behavior: should not fail because readability is appropriate for the context
    assert result.passed

# 10. Accessibility tests count missing attributes instead of computed accessible names
@pytest.mark.xfail(reason="ponytail: accessibility checks count attribute presence instead of computed accessibility names")
def test_defect_accessibility_computed_names():
    html = """<html>
    <body>
        <button aria-labelledby="label">Click</button>
        <span id="label">Submit Query</span>
    </body>
    </html>"""
    page = PageData(url="https://example.com", html=html, final_url="https://example.com", status_code=200, ttfb_ms=100, headers={})
    checker = AccessibilityChecks()
    result = checker._check_aria_labels(page)
    # Correct expected behavior: should pass because computed accessible name is provided via aria-labelledby
    assert result.passed

# 11. Unsafe generated fix code produces fictional addresses, phone numbers, ratings
@pytest.mark.xfail(reason="ponytail: generated fix code outputs fictional coordinates, phones, and placeholders")
def test_defect_fictional_data_fixes():
    html = "<html><body><h1>No Schema</h1></body></html>"
    crawl = make_crawl_result(html)
    checker = LocalSeoChecks()
    results = checker.run(crawl)
    schema_check = [r for r in results if r.check_id == "local_seo_localbusiness_schema"][0]
    # Correct expected behavior: fix code should not output fictional coordinates/addresses like "latitude: 40.7128" or "telephone: +123****7890"
    assert "40.7128" not in schema_check.fix_code
    assert "+123" not in schema_check.fix_code
