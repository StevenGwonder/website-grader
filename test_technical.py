"""Tests for TechnicalChecks — run against mock HTML."""
import pytest
from unittest.mock import patch, MagicMock

from crawler import CrawlResult, PageData, crawl_site
from checks.technical import TechnicalChecks
from checks.base import Severity

SAMPLE_GOOD = '''<html><head>
<title>Best Plumbing — Murrieta CA | Leak Repair</title>
<meta name="description" content="Best plumbing services in Murrieta, CA. Leak repair, water heaters, drain cleaning. Licensed and insured. Call (951) 555-1234.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://bestplumbing.example.com/">
<link rel="icon" href="/favicon.ico">
<meta property="og:title" content="Best Plumbing Murrieta">
<meta property="og:description" content="Best plumbing in Murrieta CA">
<meta property="og:image" content="https://bestplumbing.example.com/og.jpg">
<meta property="og:url" content="https://bestplumbing.example.com/">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{"@type":"LocalBusiness","name":"Best Plumbing","address":{"@type":"PostalAddress","streetAddress":"123 Main St","addressLocality":"Murrieta","addressRegion":"CA","postalCode":"92562"},"telephone":"9515551234"}</script>
</head><body>
<nav><a href="/about">About</a><a href="/contact">Contact</a><a href="/services">Services</a></nav>
<h1>Best Plumbing — Murrieta's Trusted Plumbers</h1>
<h2>Our Services</h2>
<p>We fix leaks, install water heaters, and handle emergencies 24/7 in Murrieta, CA.</p>
<h3>Leak Repair</h3>
<p>Fast leak detection and repair service.</p>
<a href="tel:+19515551234">(951) 555-1234</a>
</body></html>'''

SAMPLE_BAD = '<html><head></head><body><p>Hi</p></body></html>'


def make_crawl_result(html, url="https://example.com"):
    """Build a CrawlResult with one page."""
    page = PageData(url=url, html=html, final_url=url, status_code=200, ttfb_ms=100, headers={})
    result = CrawlResult(base_url=url)
    result.pages[url] = page
    return result


def test_technical_checks_run_good_site():
    """All 17 checks run and return CheckResults for a good site."""
    crawl = make_crawl_result(SAMPLE_GOOD, "https://bestplumbing.example.com")
    checker = TechnicalChecks()
    results = checker.run(crawl)
    assert len(results) == 17
    # Check that we got all check_ids
    ids = [r.check_id for r in results]
    assert "tech_meta_title" in ids
    assert "tech_schema" in ids
    assert "tech_broken_links" in ids


def test_meta_title_pass():
    """Good meta title passes."""
    crawl = make_crawl_result(SAMPLE_GOOD, "https://bestplumbing.example.com")
    checker = TechnicalChecks()
    results = checker.run(crawl)
    title_check = [r for r in results if r.check_id == "tech_meta_title"][0]
    assert title_check.passed
    assert title_check.severity == Severity.HIGH


def test_meta_title_fail():
    """Bad site fails meta title."""
    crawl = make_crawl_result(SAMPLE_BAD)
    checker = TechnicalChecks()
    results = checker.run(crawl)
    title_check = [r for r in results if r.check_id == "tech_meta_title"][0]
    assert not title_check.passed


def test_schema_detection():
    """LocalBusiness schema is detected."""
    crawl = make_crawl_result(SAMPLE_GOOD, "https://bestplumbing.example.com")
    checker = TechnicalChecks()
    results = checker.run(crawl)
    schema_check = [r for r in results if r.check_id == "tech_schema"][0]
    assert schema_check.passed
    assert schema_check.severity == Severity.CRITICAL


def test_heading_hierarchy_good():
    """Good heading hierarchy passes."""
    crawl = make_crawl_result(SAMPLE_GOOD)
    checker = TechnicalChecks()
    results = checker.run(crawl)
    heading_check = [r for r in results if r.check_id == "tech_headings"][0]
    assert heading_check.passed


def test_open_graph_tags():
    """OG tags are detected."""
    crawl = make_crawl_result(SAMPLE_GOOD, "https://bestplumbing.example.com")
    checker = TechnicalChecks()
    results = checker.run(crawl)
    og_check = [r for r in results if r.check_id == "tech_og_tags"][0]
    assert og_check.passed


def test_canonical_tag():
    """Canonical tag is detected."""
    crawl = make_crawl_result(SAMPLE_GOOD, "https://bestplumbing.example.com/")
    checker = TechnicalChecks()
    results = checker.run(crawl)
    canonical_check = [r for r in results if r.check_id == "tech_canonical"][0]
    assert canonical_check.passed


def test_dead_site_returns_empty():
    """Dead site returns empty results."""
    crawl = CrawlResult(base_url="https://dead.example.com")
    crawl.error = "timeout"
    checker = TechnicalChecks()
    results = checker.run(crawl)
    assert len(results) == 0


def test_fix_code_generated():
    """Schema check generates fix code when missing."""
    crawl = make_crawl_result(SAMPLE_BAD)
    checker = TechnicalChecks()
    results = checker.run(crawl)
    schema_check = [r for r in results if r.check_id == "tech_schema"][0]
    assert not schema_check.passed
    assert schema_check.fix_code is not None
    assert "LocalBusiness" in schema_check.fix_code