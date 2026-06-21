import pytest
from bs4 import BeautifulSoup
from crawler import CrawlResult, PageData
from classifiers import classify_page_type, classify_site_type, classify_location_model
from scoring import compute_score
from checks.local_seo import LocalSeoChecks
from checks.technical import TechnicalChecks
from checks.base import Severity
from models import FindingStatus

def make_page(url, html):
    return PageData(url=url, html=html, final_url=url, status_code=200, ttfb_ms=50, headers={})

def make_crawl(pages_dict, target_url="https://example.com"):
    crawl = CrawlResult(base_url=target_url)
    for url, html in pages_dict.items():
        crawl.pages[url] = make_page(url, html)
    return crawl

def test_page_classification():
    # 1. Homepage
    assert classify_page_type("https://example.com", "<html></html>") == "homepage"
    assert classify_page_type("https://example.com/", "<html></html>") == "homepage"
    
    # 2. About page
    assert classify_page_type("https://example.com/about-us", "<html></html>") == "about"
    assert classify_page_type("https://example.com/team", "<html></html>") == "about"
    
    # 3. Contact page
    assert classify_page_type("https://example.com/contact", "<html></html>") == "contact"
    # Form heuristics
    assert classify_page_type("https://example.com/write", '<form action="/send"><input name="email"><textarea name="message"></textarea></form>') == "contact"
    
    # 4. Service
    assert classify_page_type("https://example.com/services/plumbing", "<html></html>") == "service"
    
    # 5. Product (Schema)
    product_html = '<html><script type="application/ld+json">{"@context": "https://schema.org", "@type": "Product", "name": "Shirt"}</script></html>'
    assert classify_page_type("https://example.com/item-1", product_html) == "ecommerce_product"
    
    # 6. Policy / Utility
    assert classify_page_type("https://example.com/privacy-policy", "<html></html>") == "policy"
    assert classify_page_type("https://example.com/checkout", "<html></html>") == "utility"
    
    # Overrides
    overrides = {
        "item-1": "custom_override",
        r"/about": "about_override"
    }
    assert classify_page_type("https://example.com/item-1", product_html, overrides=overrides) == "custom_override"
    assert classify_page_type("https://example.com/about", "<html></html>", overrides=overrides) == "about_override"

def test_site_classification_and_location_model():
    # 1. National SaaS
    saas_html = '<html><head><title>Best cloud analytics SaaS platform</title></head><body><h1>Enterprise SaaS software</h1></body></html>'
    crawl_saas = make_crawl({"https://example.com": saas_html})
    site_type = classify_site_type(crawl_saas)
    assert site_type == "national_saas"
    assert classify_location_model(site_type, crawl_saas) == "national_no_local"
    
    # 2. Local storefront with map embed & address
    local_html = """<html><body>
        <h1> Murrieta Plumbers </h1>
        <p> Call us at 951-555-1234 </p>
        <p> Our office: 123 Main St, Murrieta, CA 92562 </p>
        <iframe src="https://www.google.com/maps/embed"></iframe>
    </body></html>"""
    crawl_local = make_crawl({"https://example.com": local_html})
    site_type = classify_site_type(crawl_local)
    assert site_type == "local_storefront"
    assert classify_location_model(site_type, crawl_local) == "storefront"

    # 3. Local service area business (address-less plumbing)
    plumbing_html = "<html><body><h1>Plumbing Murrieta</h1><p>Call 951-555-1234. Serving Murrieta, Temecula, and Wildomar.</p></body></html>"
    crawl_plumbing = make_crawl({"https://example.com": plumbing_html})
    site_type = classify_site_type(crawl_plumbing)
    assert site_type == "local_service_business"
    assert classify_location_model(site_type, crawl_plumbing) == "service_area"

def test_check_applicability():
    # SaaS site crawl
    saas_html = '<html><head><title>Best SaaS Platform</title></head></html>'
    crawl = make_crawl({"https://example.com": saas_html})
    
    # Local SEO check category
    checker = LocalSeoChecks()
    results = checker.run(crawl)
    
    # Since location model is national_no_local, all Local SEO checks must be NOT_APPLICABLE
    for r in results:
        assert r.status == FindingStatus.NOT_APPLICABLE
        assert r.passed is True
        assert r.score == 100
        assert r.detail == "NOT_APPLICABLE"

def test_contextual_severity():
    # Canonical check on a utility page should have adjusted lower severity (LOW)
    utility_page = make_page("https://example.com/checkout", "<html></html>")
    utility_page.page_type = "utility"
    
    checker = TechnicalChecks()
    # Mocking crawl context on checker to make it retrieve the page context
    checker.crawl_result = CrawlResult(base_url="https://example.com")
    
    # Run _check_canonical directly on utility page
    res = checker._check_canonical(utility_page)
    # Default registry severity is high, but contextually adjusted on utility page to LOW
    assert res.severity == Severity.LOW

def test_four_pillar_scoring():
    # Mock pass/fail results
    from checks.base import CheckResult
    results = [
        CheckResult(check_id="tech_meta_title", check_name="Title", category="Technical SEO", severity=Severity.HIGH, passed=True, score=100, detail=""),
        CheckResult(check_id="tech_headings", check_name="Headings", category="Technical SEO", severity=Severity.HIGH, passed=False, score=0, detail=""),
        # Local SEO checks marked NOT_APPLICABLE
        CheckResult(check_id="local_seo_maps_embed", check_name="Map", category="Local SEO", severity=Severity.HIGH, passed=True, score=100, detail="NOT_APPLICABLE", status=FindingStatus.NOT_APPLICABLE),
    ]
    
    # Health score should exclude Local SEO (since it's NOT_APPLICABLE)
    # So Health is calculated from Technical SEO checks (one pass, one fail, equal weights) -> Health = 50%
    score_data = compute_score(results)
    assert score_data["health_score"] == 50.0
    assert score_data["overall_score"] == 50
    assert score_data["coverage_score"] > 0.0
    assert score_data["confidence_score"] > 0.0
    assert score_data["opportunity_score"] > 0.0
