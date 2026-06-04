# Website Grader Pro — Full Audit Engine Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Rebuild the website grader from a 5-check toy into a 53-check professional audit tool that Steven can run from the CLI, generate a polished HTML report, and walk into client meetings armed with everything wrong with their site and exactly how to fix it.

**Architecture:** CLI tool (`grader.py`) that crawls a website (homepage + 3-5 key pages), runs 53 programmatic checks across 7 categories, generates a weighted 0-100 score, produces prioritized fix recommendations with code snippets, and outputs a self-contained HTML report. Zero API keys needed. Phase 2 adds LLM-powered analysis.

**Tech Stack:** Python 3, requests, beautifulsoup4, stdlib only (re, json, time, ssl, urllib, html, xml.etree, hashlib, textstat-like readability via stdlib)

---

## What We Can Do Programmatically (No API Keys)

### 7 Categories, 53 Checks

| Category | Checks | Critical | High | Medium | Low |
|----------|--------|----------|------|--------|-----|
| Technical SEO | 17 | 3 | 4 | 6 | 4 |
| Performance | 8 | 1 | 3 | 2 | 2 |
| Local SEO | 8 | 3 | 3 | 2 | 0 |
| Content Quality | 7 | 0 | 1 | 5 | 1 |
| Security | 3 | 1 | 2 | 0 | 0 |
| Accessibility | 5 | 0 | 1 | 2 | 2 |
| Social & Conversion | 5 | 0 | 2 | 3 | 0 |
| **Total** | **53** | **8** | **16** | **20** | **9** |

### What We CANNOT Do (Phase 2, needs API keys)
- Core Web Vitals (LCP, CLS, INP) — needs CrUX API or headless browser
- Competitive benchmarking — needs search ranking data
- AI-powered natural language recommendations — needs LLM
- Backlink analysis — needs Ahrefs/Moz API
- Keyword ranking tracking — needs search API

---

## File Structure

```
website-grader/
├── grader.py              # CLI entry point
├── crawler.py             # Multi-page crawler
├── checks/
│   ├── __init__.py         # Check registry, base classes
│   ├── technical.py        # 17 technical SEO checks
│   ├── performance.py      # 8 performance checks
│   ├── local_seo.py        # 8 local SEO checks
│   ├── content.py          # 7 content quality checks
│   ├── security.py         # 3 security checks
│   ├── accessibility.py    # 5 accessibility checks
│   └── conversion.py       # 5 social/conversion checks
├── scoring.py              # Weighted scoring engine (0-100)
├── fixes.py                # Code snippet generation for fixes
├── report.py               # HTML report generator
├── report_template.html    # HTML report template (Jinja2-free, string-based)
├── test_crawler.py         # Crawler tests
├── test_checks.py          # Check tests (one per check)
├── test_scoring.py         # Scoring tests
├── test_report.py          # Report generation tests
├── requirements.txt        # flask, requests, beautifulsoup4
└── README.md               # Updated docs
```

---

## Task 1: Project Scaffolding

**Objective:** Create directory structure, base check framework, and check registry.

**Files:**
- Create: `website-grader/checks/__init__.py`
- Create: `website-grader/checks/base.py`

**Step 1: Create checks package init with registry**

`checks/__init__.py`:
```python
from .technical import TechnicalChecks
from .performance import PerformanceChecks
from .local_seo import LocalSeoChecks
from .content import ContentChecks
from .security import SecurityChecks
from .accessibility import AccessibilityChecks
from .conversion import ConversionChecks

ALL_CHECK_CATEGORIES = [
    TechnicalChecks,
    PerformanceChecks,
    LocalSeoChecks,
    ContentChecks,
    SecurityChecks,
    AccessibilityChecks,
    ConversionChecks,
]
```

**Step 2: Create base check framework**

`checks/base.py`:
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class CheckResult:
    check_id: str
    check_name: str
    category: str
    severity: Severity
    passed: bool
    score: int  # 0-100 for this individual check
    detail: str  # What we found
    recommendation: str  # What to do about it
    fix_code: Optional[str] = None  # Generated fix snippet
    fix_difficulty: str = ""  # "Easy (5 min)", "Medium (1 hr)", "Hard (2+ hrs)"
    impact_estimate: str = ""  # "Can increase call volume 20-40%"
    data: dict = field(default_factory=dict)  # Raw data for report

class CheckCategory:
    """Base class for a category of checks."""
    category_name: str = ""
    category_weight: int = 0  # Relative weight in overall score

    def run(self, crawl_result) -> list[CheckResult]:
        """Run all checks in this category. Returns list of CheckResult."""
        raise NotImplementedError
```

**Step 3: Verify it imports**
Run: `python3 -c "from checks.base import CheckResult, Severity, CheckCategory; print('OK')"`
Expected: `OK`

**Step 4: Commit**
```bash
git add checks/__init__.py checks/base.py
git commit -m "feat: add check framework base classes"
```

---

## Task 2: Multi-Page Crawler

**Objective:** Crawl homepage, extract internal links, fetch 3-5 key pages (about, contact, services, + 1 more). Return structured data for all checks to use.

**Files:**
- Create: `website-grader/crawler.py`
- Create: `website-grader/test_crawler.py`

**Step 1: Write failing tests**

`test_crawler.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from crawler import CrawlResult, PageData, crawl_site

SAMPLE_HOMEPAGE = '''<html><head><title>Test Site</title></head><body>
<a href="/about">About</a><a href="/contact">Contact</a>
<a href="/services">Services</a><a href="https://external.com">Ext</a>
<p>Hello world content here with enough words to pass the word count check.
More content more content more content more content more content.</p>
</body></html>'''

SAMPLE_ABOUT = '<html><head><title>About</title></head><body><p>About us</p></body></html>'

def test_crawl_result_defaults():
    result = CrawlResult("https://example.com")
    assert result.base_domain == "example.com"
    assert len(result.pages) == 0

def test_crawl_extracts_internal_links():
    mock_resp = MagicMock(text=SAMPLE_HOMEPAGE, url="https://example.com", status_code=200)
    with patch("crawler.req.get", return_value=mock_resp):
        result = crawl_site("https://example.com", max_pages=3)
    assert "https://example.com" in result.pages
    assert len(result.pages) >= 1

def test_external_links_not_crawled():
    mock_resp = MagicMock(text=SAMPLE_HOMEPAGE, url="https://example.com", status_code=200)
    with patch("crawler.req.get", return_value=mock_resp):
        result = crawl_site("https://example.com", max_pages=5)
    assert "https://external.com" not in result.pages

def test_dead_site_handled():
    with patch("crawler.req.get", side_effect=Exception("timeout")):
        result = crawl_site("https://dead.example.com")
    assert result.error is not None
```

**Step 2: Run tests to verify failure**
Run: `pytest test_crawler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'crawler'`

**Step 3: Implement crawler**

`crawler.py`:
```python
"""Multi-page crawler — fetches homepage + key linked pages."""
import time
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests as req
from bs4 import BeautifulSoup

# Key page patterns to prioritize when crawling
PRIORITY_PATHS = [
    r"/about", r"/contact", r"/services", r"/service",
    r"/team", r"/faq", r"/blog", r"/portfolio",
]

@dataclass
class PageData:
    url: str
    html: str
    final_url: str
    status_code: int
    ttfb_ms: float  # Time to first byte in milliseconds
    headers: dict
    soup: BeautifulSoup = None
    error: str = None

    def __post_init__(self):
        if self.html and not self.soup:
            self.soup = BeautifulSoup(self.html, "html.parser")

@dataclass
class CrawlResult:
    base_url: str
    base_domain: str = ""
    pages: dict = field(default_factory=dict)  # url -> PageData
    robots_txt: str = ""
    sitemap_xml: str = ""
    sitemap_urls: list = field(default_factory=list)
    error: str = None

    def __post_init__(self):
        self.base_domain = urlparse(self.base_url).netloc

    @property
    def homepage(self) -> PageData | None:
        return self.pages.get(self.base_url)

    def all_links(self) -> set:
        """Return all unique internal links found across all pages."""
        links = set()
        for page in self.pages.values():
            if page.soup:
                for a in page.soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("/") or self.base_domain in href:
                        links.add(urljoin(page.url, href))
        return links

def _fetch_page(url, timeout=10):
    """Fetch a single page, return PageData with timing."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    start = time.monotonic()
    try:
        resp = req.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        ttfb = (time.monotonic() - start) * 1000
        return PageData(
            url=url, html=resp.text, final_url=resp.url,
            status_code=resp.status_code, ttfb_ms=round(ttfb, 1),
            headers=dict(resp.headers),
        )
    except Exception as e:
        ttfb = (time.monotonic() - start) * 1000
        return PageData(
            url=url, html="", final_url=url, status_code=0,
            ttfb_ms=round(ttfb, 1), headers={}, error=str(e),
        )

def _extract_internal_links(soup, base_url, base_domain):
    """Extract same-domain links from a page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full_url = urljoin(base_url, href)
        if urlparse(full_url).netloc == base_domain:
            links.append(full_url)
    return links

def crawl_site(url, max_pages=5, timeout=10):
    """Crawl a site: homepage + up to max_pages key pages. Returns CrawlResult."""
    if not url.startswith("http"):
        url = "https://" + url
    result = CrawlResult(base_url=url)

    # Fetch homepage
    homepage = _fetch_page(url, timeout)
    result.pages[url] = homepage
    if homepage.error:
        result.error = homepage.error
        return result

    # Fetch robots.txt
    robots_url = url.rstrip("/") + "/robots.txt"
    try:
        robots_resp = req.get(robots_url, timeout=timeout)
        if robots_resp.status_code == 200:
            result.robots_txt = robots_resp.text
    except Exception:
        pass

    # Fetch sitemap.xml
    sitemap_url = url.rstrip("/") + "/sitemap.xml"
    try:
        sitemap_resp = req.get(sitemap_url, timeout=timeout)
        if sitemap_resp.status_code == 200:
            result.sitemap_xml = sitemap_resp.text
            # Extract URLs from sitemap
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(sitemap_resp.text)
                ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                for loc in root.findall(".//sm:loc", ns):
                    result.sitemap_urls.append(loc.text)
            except ET.ParseError:
                pass
    except Exception:
        pass

    # Extract internal links from homepage
    internal_links = _extract_internal_links(homepage.soup, url, result.base_domain)

    # Prioritize key pages (about, contact, services)
    priority_links = []
    other_links = []
    for link in internal_links:
        if any(re.search(pat, link, re.I) for pat in PRIORITY_PATHS):
            priority_links.append(link)
        else:
            other_links.append(link)

    # Crawl priority pages first, then fill remaining
    to_crawl = (priority_links + other_links)[:max_pages - 1]  # -1 for homepage
    for link_url in to_crawl:
        if link_url in result.pages:
            continue
        page = _fetch_page(link_url, timeout)
        if not page.error:
            result.pages[link_url] = page

    return result
```

**Step 4: Run tests**
Run: `pytest test_crawler.py -v`
Expected: 4 passed

**Step 5: Commit**
```bash
git add crawler.py test_crawler.py
git commit -m "feat: add multi-page crawler"
```

---

## Task 3: Technical SEO Checks (17 checks)

**Objective:** Implement all 17 technical SEO checks.

**Files:**
- Create: `website-grader/checks/technical.py`

**Checks to implement:**

| # | Check | Severity | Method |
|---|-------|----------|--------|
| 1 | Meta Title | HIGH | `soup.find('title')` — check length 30-60, not generic, keyword presence |
| 2 | Meta Description | HIGH | `soup.find('meta', name='description')` — length 120-160, keyword presence |
| 3 | Heading Hierarchy | HIGH | `soup.find_all(['h1'-'h6'])` — exactly 1 H1, no skipped levels |
| 4 | Canonical Tag | MEDIUM | `soup.find('link', rel='canonical')` — exists, points to correct URL |
| 5 | Robots Meta | MEDIUM | `soup.find('meta', name='robots')` — check for noindex/nofollow |
| 6 | Schema/Structured Data | CRITICAL | `soup.find_all('script', type='application/ld+json')` — parse JSON-LD, check for LocalBusiness, Organization, FAQ, Breadcrumb, Service |
| 7 | Open Graph Tags | MEDIUM | `soup.find_all('meta', attrs={'property':re.compile('og:')})` — og:title, og:description, og:image, og:url |
| 8 | Twitter Cards | LOW | `soup.find('meta', attrs={'name':re.compile('twitter:')})` — twitter:card, twitter:title |
| 9 | Favicon | LOW | `soup.find('link', rel=re.compile('icon'))` — exists |
| 10 | XML Sitemap | HIGH | `crawl_result.sitemap_xml` — exists, valid XML, contains URLs |
| 11 | Robots.txt | MEDIUM | `crawl_result.robots_txt` — exists, references sitemap, no wildcards blocking |
| 12 | Broken Links | CRITICAL | Extract all links from all pages, GET each, check status codes |
| 13 | Redirect Chains | MEDIUM | `resp.history` — no chains >1 hop |
| 14 | Internal Link Structure | MEDIUM | Count internal links, check distribution across pages, anchor text diversity |
| 15 | URL Structure | LOW | Parse hrefs — no long query strings, descriptive slugs, no .html extensions |
| 16 | Pagination | LOW | `soup.find('link', rel='next')` / `rel='prev'` — exists on multi-page content |
| 17 | Breadcrumbs | MEDIUM | `soup.find(class_=re.compile('breadcrumb'))` or BreadcrumbList schema |

**Implementation skeleton:**

`checks/technical.py`:
```python
"""17 Technical SEO checks — all programmable, no API keys."""
import re
import json
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

import requests as req
from bs4 import BeautifulSoup

from .base import CheckResult, Severity, CheckCategory


class TechnicalChecks(CheckCategory):
    category_name = "Technical SEO"
    category_weight = 25  # 25% of overall score

    def run(self, crawl_result) -> list[CheckResult]:
        results = []
        homepage = crawl_result.homepage
        if not homepage or not homepage.soup:
            return results

        results.append(self._check_meta_title(homepage))
        results.append(self._check_meta_description(homepage))
        results.append(self._check_heading_hierarchy(homepage))
        results.append(self._check_canonical(homepage))
        results.append(self._check_robots_meta(homepage))
        results.append(self._check_schema(homepage))
        results.append(self._check_open_graph(homepage))
        results.append(self._check_twitter_cards(homepage))
        results.append(self._check_favicon(homepage))
        results.append(self._check_sitemap(crawl_result))
        results.append(self._check_robots_txt(crawl_result))
        results.append(self._check_broken_links(crawl_result))
        results.append(self._check_redirect_chains(crawl_result))
        results.append(self._check_internal_links(crawl_result))
        results.append(self._check_url_structure(crawl_result))
        results.append(self._check_pagination(homepage))
        results.append(self._check_breadcrumbs(homepage))
        return results

    def _check_meta_title(self, page):
        title_tag = page.soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        passed = 30 <= len(title) <= 60 and title.lower() not in ("home", "untitled", "")
        return CheckResult(
            check_id="tech_meta_title",
            check_name="Meta Title",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=100 if passed else 0,
            detail=f'Found: "{title}" ({len(title)} chars)' if title else "No <title> tag found",
            recommendation="Title should be 30-60 chars, include target keywords, and be unique per page." if not passed else "",
            fix_code=f'<title>{title[:60]}</title>' if title else "<title>Your Business — Service in City, ST</title>",
            fix_difficulty="Easy (2 min)",
            impact_estimate="Critical — this is what shows in Google results and browser tabs",
            data={"title": title, "length": len(title)},
        )

    def _check_meta_description(self, page):
        meta = page.soup.find("meta", attrs={"name": "description"})
        desc = meta.get("content", "") if meta else ""
        passed = 120 <= len(desc) <= 160 and len(desc) > 0
        return CheckResult(
            check_id="tech_meta_desc",
            check_name="Meta Description",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=100 if passed else 0,
            detail=f'Found: "{desc[:80]}..." ({len(desc)} chars)' if desc else "No meta description found",
            recommendation="Description should be 120-160 chars with a compelling CTR-optimized summary." if not passed else "",
            fix_code=f'<meta name="description" content="{desc[:160]}">' if desc else '<meta name="description" content="Your business description with keywords and call to action.">',
            fix_difficulty="Easy (5 min)",
            impact_estimate="High — directly affects click-through rate from Google results",
            data={"description": desc, "length": len(desc)},
        )

    def _check_heading_hierarchy(self, page):
        headings = page.soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        h1_count = len(page.soup.find_all("h1"))
        # Check for skipped levels (e.g., h1 → h3 with no h2)
        levels = [int(h.name[1]) for h in headings]
        skipped = False
        for i in range(1, len(levels)):
            if levels[i] - levels[i-1] > 1:
                skipped = True
                break
        passed = h1_count == 1 and not skipped
        return CheckResult(
            check_id="tech_headings",
            check_name="Heading Hierarchy",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=100 if passed else 50,
            detail=f"H1 count: {h1_count}, total headings: {len(headings)}, skipped levels: {skipped}",
            recommendation="Use exactly one H1 per page. Don't skip heading levels (H1→H3 is bad). Use H2 for sections, H3 for subsections." if not passed else "",
            fix_difficulty="Medium (30 min)",
            impact_estimate="Medium — heading structure helps Google understand content hierarchy",
            data={"h1_count": h1_count, "heading_count": len(headings), "levels": levels},
        )

    def _check_canonical(self, page):
        canonical = page.soup.find("link", rel="canonical")
        canonical_url = canonical.get("href", "") if canonical else ""
        passed = bool(canonical_url) and canonical_url == page.final_url
        return CheckResult(
            check_id="tech_canonical",
            check_name="Canonical Tag",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=100 if passed else 0,
            detail=f'Canonical: "{canonical_url}"' if canonical else "No canonical tag found",
            recommendation="Add <link rel=\"canonical\" href=\"https://yourdomain.com/page\"> to prevent duplicate content issues." if not passed else "",
            fix_code=f'<link rel="canonical" href="{page.final_url}">',
            fix_difficulty="Easy (2 min)",
            impact_estimate="Medium — prevents Google from indexing duplicate URLs",
            data={"canonical_url": canonical_url},
        )

    def _check_robots_meta(self, page):
        meta = page.soup.find("meta", attrs={"name": "robots"})
        content = meta.get("content", "") if meta else ""
        has_noindex = "noindex" in content.lower()
        has_nofollow = "nofollow" in content.lower()
        passed = not has_noindex and not has_nofollow
        return CheckResult(
            check_id="tech_robots_meta",
            check_name="Robots Meta Directive",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=100 if passed else 0,
            detail=f'Robots meta: "{content}"' if meta else "No robots meta tag (this is fine — default is index,follow)",
            recommendation="Remove noindex/nofollow directives if you want this page indexed." if not passed else "",
            data={"content": content, "noindex": has_noindex, "nofollow": has_nofollow},
        )

    def _check_schema(self, page):
        schemas = page.soup.find_all("script", type="application/ld+json")
        schema_types = []
        valid_schemas = []
        for s in schemas:
            try:
                data = json.loads(s.string or s.get_text() or "{}")
                if isinstance(data, list):
                    for item in data:
                        t = item.get("@type", "")
                        schema_types.append(t)
                        valid_schemas.append(item)
                elif isinstance(data, dict):
                    t = data.get("@type", "")
                    schema_types.append(t)
                    valid_schemas.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

        has_local_business = any("LocalBusiness" in t or "Organization" in t for t in schema_types)
        has_faq = any("FAQPage" in t for t in schema_types)
        has_breadcrumb = any("BreadcrumbList" in t for t in schema_types)

        score = 0
        if has_local_business: score += 50
        if has_faq: score += 25
        if has_breadcrumb: score += 25
        if not schemas: score = 0

        passed = score >= 50  # At least LocalBusiness or Organization

        return CheckResult(
            check_id="tech_schema",
            check_name="Schema / Structured Data",
            category=self.category_name,
            severity=Severity.CRITICAL,
            passed=passed,
            score=score,
            detail=f"Found {len(schemas)} schema blocks: {', '.join(schema_types) if schema_types else 'none'}",
            recommendation="Add LocalBusiness schema with name, address, phone, geo, and hours. Add FAQ schema for FAQ sections. Use Google's Rich Results Test to validate." if not passed else "",
            fix_code=self._generate_local_business_schema(page),
            fix_difficulty="Medium (30 min)",
            impact_estimate="Critical — schema helps Google understand your business and enables rich snippets in search results",
            data={"schema_types": schema_types, "valid_schemas": valid_schemas},
        )

    def _generate_local_business_schema(self, page):
        """Generate LocalBusiness JSON-LD schema snippet."""
        # Try to extract NAP from page
        soup = page.soup
        name = ""
        title_tag = soup.find("title")
        if title_tag:
            name = title_tag.get_text(strip=True).split("—")[0].strip()

        phone = ""
        tel = soup.find("a", href=re.compile(r"^tel:"))
        if tel:
            phone = tel.get("href", "").replace("tel:", "")

        return json.dumps({
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": name or "Your Business Name",
            "telephone": phone or "+1-555-555-5555",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Main St",
                "addressLocality": "City",
                "addressRegion": "ST",
                "postalCode": "00000",
                "addressCountry": "US"
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": 0.0,
                "longitude": 0.0
            },
            "openingHoursSpecification": [{
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
                "opens": "08:00",
                "closes": "17:00"
            }],
            "url": page.final_url
        }, indent=2)

    def _check_open_graph(self, page):
        og_tags = page.soup.find_all("meta", attrs={"property": re.compile(r"^og:")})
        og_keys = [t.get("property") for t in og_tags]
        required = ["og:title", "og:description", "og:image", "og:url"]
        missing = [k for k in required if k not in og_keys]
        passed = not missing
        return CheckResult(
            check_id="tech_og_tags",
            check_name="Open Graph Tags",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=100 if passed else (len(required) - len(missing)) * 25,
            detail=f"Found: {', '.join(og_keys) if og_keys else 'none'}. Missing: {', '.join(missing) if missing else 'none'}",
            recommendation="Add Open Graph tags for social media sharing. Facebook and LinkedIn use these for link previews." if not passed else "",
            fix_code='\n'.join([f'<meta property="{k}" content="">' for k in missing]),
            fix_difficulty="Easy (5 min)",
            impact_estimate="Medium — affects how links appear when shared on social media",
            data={"og_keys": og_keys, "missing": missing},
        )

    def _check_twitter_cards(self, page):
        tw_tags = page.soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})
        tw_keys = [t.get("name") for t in tw_tags]
        passed = "twitter:card" in tw_keys
        return CheckResult(
            check_id="tech_twitter_cards",
            check_name="Twitter Cards",
            category=self.category_name,
            severity=Severity.LOW,
            passed=passed,
            score=100 if passed else 0,
            detail=f"Found: {', '.join(tw_keys) if tw_keys else 'none'}",
            recommendation="Add Twitter Card meta tags for better social sharing." if not passed else "",
            fix_code='<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="">\n<meta name="twitter:image" content="">',
            fix_difficulty="Easy (3 min)",
            impact_estimate="Low — affects Twitter/X link previews",
            data={"twitter_keys": tw_keys},
        )

    def _check_favicon(self, page):
        icon = page.soup.find("link", rel=re.compile(r"icon", re.I))
        passed = bool(icon)
        return CheckResult(
            check_id="tech_favicon",
            check_name="Favicon",
            category=self.category_name,
            severity=Severity.LOW,
            passed=passed,
            score=100 if passed else 0,
            detail=f'Favicon: "{icon.get("href")}"' if icon else "No favicon found",
            recommendation="Add a favicon. It shows in browser tabs and bookmarks." if not passed else "",
            fix_code='<link rel="icon" href="/favicon.ico" type="image/x-icon">',
            fix_difficulty="Easy (5 min)",
            impact_estimate="Low — branding consistency in browser tabs",
            data={"favicon_href": icon.get("href") if icon else None},
        )

    def _check_sitemap(self, crawl_result):
        has_sitemap = bool(crawl_result.sitemap_xml)
        url_count = len(crawl_result.sitemap_urls)
        passed = has_sitemap and url_count > 0
        return CheckResult(
            check_id="tech_sitemap",
            check_name="XML Sitemap",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=100 if passed else 0,
            detail=f"Sitemap found with {url_count} URLs" if has_sitemap else "No sitemap.xml found",
            recommendation="Create an XML sitemap at /sitemap.xml listing all your pages. Submit it in Google Search Console." if not passed else "",
            fix_code="<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n  <url><loc>https://yourdomain.com/</loc></url>\n</urlset>",
            fix_difficulty="Easy (10 min)",
            impact_estimate="High — helps Google discover and index all your pages",
            data={"has_sitemap": has_sitemap, "url_count": url_count, "urls": crawl_result.sitemap_urls[:20]},
        )

    def _check_robots_txt(self, crawl_result):
        has_robots = bool(crawl_result.robots_txt)
        references_sitemap = "sitemap" in crawl_result.robots_txt.lower() if has_robots else False
        passed = has_robots
        score = 100 if (has_robots and references_sitemap) else (50 if has_robots else 0)
        return CheckResult(
            check_id="tech_robots_txt",
            check_name="Robots.txt",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=score,
            detail=f"robots.txt found, references sitemap: {references_sitemap}" if has_robots else "No robots.txt found",
            recommendation="Create /robots.txt with a reference to your sitemap." if not passed else ("Add sitemap reference to robots.txt" if not references_sitemap else ""),
            fix_code="User-agent: *\nAllow: /\n\nSitemap: https://yourdomain.com/sitemap.xml",
            fix_difficulty="Easy (2 min)",
            impact_estimate="Medium — controls crawler behavior and points to sitemap",
            data={"has_robots": has_robots, "references_sitemap": references_sitemap},
        )

    def _check_broken_links(self, crawl_result):
        """Check all links across all pages for 404s and 500s."""
        all_links = set()
        for page in crawl_result.pages.values():
            if not page.soup:
                continue
            for a in page.soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                    continue
                full_url = urljoin(page.url, href)
                if full_url.startswith("http"):
                    all_links.add(full_url)

        broken = []
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        for link in all_links:
            try:
                resp = req.head(link, headers=headers, timeout=5, allow_redirects=True)
                if resp.status_code >= 400:
                    broken.append({"url": link, "status": resp.status_code})
            except Exception:
                broken.append({"url": link, "status": "error"})

        passed = len(broken) == 0
        return CheckResult(
            check_id="tech_broken_links",
            check_name="Broken Links",
            category=self.category_name,
            severity=Severity.CRITICAL,
            passed=passed,
            score=100 if passed else max(0, 100 - len(broken) * 20),
            detail=f"Checked {len(all_links)} links, found {len(broken)} broken" if all_links else "No links found to check",
            recommendation=f"Fix {len(broken)} broken links. These hurt UX and SEO." if broken else "",
            fix_code="\n".join([f"<!-- Fix: {b['url']} returned {b['status']} -->" for b in broken[:5]]),
            fix_difficulty="Medium (varies)",
            impact_estimate="Critical — broken links hurt user experience and crawl budget",
            data={"total_links": len(all_links), "broken_links": broken},
        )

    def _check_redirect_chains(self, crawl_result):
        chains = []
        for url, page in crawl_result.pages.items():
            # PageData doesn't store redirect history; check final_url vs url
            if page.final_url and page.final_url != url:
                chains.append({"from": url, "to": page.final_url})
        passed = len(chains) <= 1  # Homepage redirect to www or https is fine
        return CheckResult(
            check_id="tech_redirects",
            check_name="Redirect Chains",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=100 if passed else 50,
            detail=f"Found {len(chains)} redirects" if chains else "No redirect chains detected",
            recommendation="Minimize redirects. Each redirect adds latency. Direct links are better than chains." if not passed else "",
            fix_difficulty="Medium",
            impact_estimate="Medium — redirect chains add latency and dilute link equity",
            data={"redirects": chains},
        )

    def _check_internal_links(self, crawl_result):
        total_internal = 0
        anchor_texts = []
        for page in crawl_result.pages.values():
            if not page.soup:
                continue
            for a in page.soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/") or crawl_result.base_domain in href:
                    total_internal += 1
                    anchor_texts.append(a.get_text(strip=True))

        unique_anchors = len(set(anchor_texts))
        passed = total_internal >= 10 and unique_anchors >= 5
        return CheckResult(
            check_id="tech_internal_links",
            check_name="Internal Link Structure",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=100 if passed else max(0, min(100, total_internal * 10)),
            detail=f"{total_internal} internal links with {unique_anchors} unique anchor texts across {len(crawl_result.pages)} pages",
            recommendation="Add more internal links between related pages. Use descriptive anchor text, not 'click here'." if not passed else "",
            fix_difficulty="Medium (1 hr)",
            impact_estimate="Medium — internal links help Google understand site structure and distribute authority",
            data={"total_internal_links": total_internal, "unique_anchors": unique_anchors},
        )

    def _check_url_structure(self, crawl_result):
        issues = []
        for url in crawl_result.pages.keys():
            parsed = urlparse(url)
            path = parsed.path
            # Check for .html extension
            if path.endswith(".html") or path.endswith(".htm"):
                issues.append(f"{url} — .html extension (use clean URLs)")
            # Check for long query strings
            if len(parsed.query) > 100:
                issues.append(f"{url} — long query string")
            # Check for non-descriptive slugs
            if re.match(r"/\?p=\d+", path) or re.match(r"/\d+$", path):
                issues.append(f"{url} — non-descriptive URL slug")
        passed = len(issues) == 0
        return CheckResult(
            check_id="tech_url_structure",
            check_name="URL Structure",
            category=self.category_name,
            severity=Severity.LOW,
            passed=passed,
            score=100 if passed else max(0, 100 - len(issues) * 25),
            detail=f"{len(issues)} URL structure issues found" if issues else "URLs are clean and descriptive",
            recommendation="Use clean URLs: /services/plumbing-repair not /?p=123 or /services.html" if issues else "",
            fix_difficulty="Medium",
            impact_estimate="Low — clean URLs are slightly better for SEO and UX",
            data={"issues": issues},
        )

    def _check_pagination(self, page):
        next_link = page.soup.find("link", rel="next")
        prev_link = page.soup.find("link", rel="prev")
        has_pagination = bool(next_link or prev_link)
        # Pagination is optional — only flag if site has blog/content sections
        return CheckResult(
            check_id="tech_pagination",
            check_name="Pagination Tags",
            category=self.category_name,
            severity=Severity.LOW,
            passed=True,  # Not failing — informational
            score=100 if has_pagination else 50,
            detail=f"Pagination tags: next={'yes' if next_link else 'no'}, prev={'yes' if prev_link else 'no'}",
            recommendation="If you have multi-page content (blog, portfolio), add rel=next/prev tags." if not has_pagination else "",
            data={"has_next": bool(next_link), "has_prev": bool(prev_link)},
        )

    def _check_breadcrumbs(self, page):
        breadcrumb_html = page.soup.find(class_=re.compile(r"breadcrumb", re.I))
        # Also check for BreadcrumbList schema
        schemas = page.soup.find_all("script", type="application/ld+json")
        has_breadcrumb_schema = False
        for s in schemas:
            try:
                data = json.loads(s.string or s.get_text() or "{}")
                if isinstance(data, dict) and "BreadcrumbList" in str(data.get("@type", "")):
                    has_breadcrumb_schema = True
            except (json.JSONDecodeError, TypeError):
                pass
        has_breadcrumbs = bool(breadcrumb_html) or has_breadcrumb_schema
        return CheckResult(
            check_id="tech_breadcrumbs",
            check_name="Breadcrumbs",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=has_breadcrumbs,
            score=100 if has_breadcrumbs else 0,
            detail=f"HTML breadcrumbs: {bool(breadcrumb_html)}, Schema breadcrumbs: {has_breadcrumb_schema}",
            recommendation="Add breadcrumb navigation. It helps users and Google understand site structure. Add BreadcrumbList schema for rich snippets." if not has_breadcrumbs else "",
            fix_difficulty="Medium (1 hr)",
            impact_estimate="Medium — improves navigation UX and enables breadcrumb rich snippets in Google",
            data={"html_breadcrumbs": bool(breadcrumb_html), "schema_breadcrumbs": has_breadcrumb_schema},
        )
```

**Step 4: Run tests (write at least 3 tests for technical checks)**
Run: `pytest test_checks.py -v -k technical`
Expected: PASS

**Step 5: Commit**
```bash
git add checks/technical.py test_checks.py
git commit -m "feat: add 17 technical SEO checks"
```

---

## Task 4: Performance Checks (8 checks)

**Objective:** Implement all 8 performance checks — measuring real HTTP response metrics.

**Files:**
- Create: `website-grader/checks/performance.py`

**Checks:**

| # | Check | Severity | Method |
|---|-------|----------|--------|
| 1 | TTFB | CRITICAL | `page.ttfb_ms` — already captured by crawler. <200ms excellent, <500ms good, <1s acceptable, >1s poor |
| 2 | Page Weight | HIGH | `len(page.html)` in bytes. <500KB good, <1.5MB acceptable, >1.5MB poor |
| 3 | Gzip/Brotli | HIGH | `page.headers.get('content-encoding')` — gzip or br |
| 4 | Cache Headers | MEDIUM | `page.headers.get('cache-control')`, `page.headers.get('etag')` |
| 5 | Image Optimization | HIGH | Parse `<img>` tags, check format (webp vs jpg/png), lazy loading attr, count |
| 6 | CSS/JS Resource Count | MEDIUM | Count `<link rel=stylesheet>` + `<script src>`, check async/defer |
| 7 | HTML Minification | LOW | Whitespace ratio in HTML |
| 8 | Server Header | LOW | `page.headers.get('server')` — informational |

**Implementation follows the same pattern as Task 3.** Key differences:

- TTFB is already captured in `PageData.ttfb_ms` from the crawler
- Image analysis checks `<img>` tags: format from src extension, `loading="lazy"` attribute
- CSS/JS count: `soup.find_all('link', rel='stylesheet')` + `soup.find_all('script', src=True)`, check for `async`/`defer` on scripts

**Commit:**
```bash
git add checks/performance.py
git commit -m "feat: add 8 performance checks"
```

---

## Task 5: Local SEO Checks (8 checks)

**Objective:** Implement all 8 local SEO checks — the most important category for trades businesses.

**Files:**
- Create: `website-grader/checks/local_seo.py`

**Checks:**

| # | Check | Severity | Method |
|---|-------|----------|--------|
| 1 | NAP Extraction | CRITICAL | Parse schema JSON-LD or regex for phone (`\d{3}[-.]?\d{3}[-.]?\d{4}`), address (street+city+state+zip pattern), business name (from title/schema) |
| 2 | NAP Consistency | CRITICAL | Compare NAP across ALL crawled pages — same name, phone, address everywhere? |
| 3 | LocalBusiness Schema | CRITICAL | Parse JSON-LD for `@type: LocalBusiness` with required fields (name, address, phone, geo, hours) |
| 4 | Google Maps Embed | HIGH | `soup.find('iframe', src=re.compile('google.*maps'))` |
| 5 | Service Area Keywords | HIGH | Regex for city/county/region names in content text — need a list of common patterns |
| 6 | City/Region Targeting | HIGH | Check if city/region appears in title tag, H1, or meta description |
| 7 | Review Schema | MEDIUM | Parse JSON-LD for `Review` or `AggregateRating` |
| 8 | Google Business Profile Link | MEDIUM | `soup.find('a', href=re.compile('google.*business|maps.google'))` |

**NAP extraction approach:**
```python
# Phone: regex r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}' — filter out tel: href values
# Address: regex for street number + street name + city + state + zip pattern
#   r'\d+\s+[A-Z][a-z]+\s+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Cir)\.?,?\s+([A-Z][a-z]+,\s+[A-Z]{2}\s+\d{5})'
# Name: from JSON-LD schema, or <title> tag, or <h1>
```

**NAP consistency check:**
- Extract NAP from each crawled page
- Compare across pages — flag mismatches
- Generate a table showing NAP per page

**Commit:**
```bash
git add checks/local_seo.py
git commit -m "feat: add 8 local SEO checks"
```

---

## Task 6: Content Quality Checks (7 checks)

**Objective:** Implement content quality checks.

**Files:**
- Create: `website-grader/checks/content.py`

**Checks:**

| # | Check | Severity | Method |
|---|-------|----------|--------|
| 1 | Word Count | HIGH | `len(text.split())` — <200 thin, 200-800 ok, >800 good. Check per page. |
| 2 | Keyword Density | MEDIUM | Extract top 10 words (excluding stopwords), count frequency. Flag if one word >5% (stuffing) or no clear topic. |
| 3 | Readability (Flesch) | MEDIUM | Count sentences, syllables (estimate via vowel groups), compute Flesch Reading Ease. 60+ readable, <30 difficult. |
| 4 | FAQ Presence | MEDIUM | `soup.find(class_=re.compile('faq'))` or FAQPage schema |
| 5 | E-E-A-T Signals | MEDIUM | Check for: author bio, about page link, license/cert number, years in business, trust badges (BBB, certified, bonded, insured) |
| 6 | Content Uniqueness | MEDIUM | Hash text of each page, compare hashes. If two pages >80% similar, flag. |
| 7 | Title-Content Alignment | LOW | Extract keywords from title/H1, check if they appear in body text |

**Readability implementation (pure stdlib):**
```python
import re

def flesch_reading_ease(text):
    """Compute Flesch Reading Ease score. 60+ = readable, <30 = difficult."""
    sentences = len(re.findall(r'[.!?]+', text))
    words = len(text.split())
    if sentences == 0 or words == 0:
        return 0
    # Estimate syllables: count vowel groups
    syllables = sum(len(re.findall(r'[aeiouAEIOU]+', word)) for word in text.split())
    if syllables == 0:
        return 0
    return 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
```

**Commit:**
```bash
git add checks/content.py
git commit -m "feat: add 7 content quality checks"
```

---

## Task 7: Security Checks (3 checks)

**Objective:** Implement security checks.

**Files:**
- Create: `website-grader/checks/security.py`

**Checks:**

| # | Check | Severity | Method |
|---|-------|----------|--------|
| 1 | SSL Certificate | CRITICAL | Check if HTTPS worked, cert validity. `ssl` module or just `resp.url.startswith('https://')` |
| 2 | Security Headers | HIGH | Parse response headers for: CSP, HSTS (`Strict-Transport-Security`), `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` |
| 3 | Mixed Content | HIGH | Find `http://` resources (images, scripts, CSS) on HTTPS pages |

**Security headers check:**
```python
SECURITY_HEADERS = {
    "content-security-policy": {"severity": Severity.HIGH, "name": "Content-Security-Policy"},
    "strict-transport-security": {"severity": Severity.HIGH, "name": "HSTS"},
    "x-frame-options": {"severity": Severity.MEDIUM, "name": "X-Frame-Options"},
    "x-content-type-options": {"severity": Severity.MEDIUM, "name": "X-Content-Type-Options"},
    "referrer-policy": {"severity": Severity.LOW, "name": "Referrer-Policy"},
}
```

**Commit:**
```bash
git add checks/security.py
git commit -m "feat: add 3 security checks"
```

---

## Task 8: Accessibility Checks (5 checks)

**Objective:** Implement accessibility checks from HTML analysis.

**Files:**
- Create: `website-grader/checks/accessibility.py`

**Checks:**

| # | Check | Severity | Method |
|---|-------|----------|--------|
| 1 | Image Alt Text | HIGH | `soup.find_all('img')` — check `alt` attribute exists and is not empty |
| 2 | Form Labels | MEDIUM | `soup.find_all('input')` — check associated `<label>` or `aria-label` |
| 3 | Heading Order | MEDIUM | Analyze h1→h2→h3 sequence for skipped levels (overlaps with technical, but different severity lens) |
| 4 | ARIA Labels | LOW | `soup.find_all(attrs={'aria-label': True, 'role': True})` — check interactive elements have labels |
| 5 | Skip Navigation | LOW | `soup.find('a', href='#main')` or `soup.find('a', href='#content')` |

**Commit:**
```bash
git add checks/accessibility.py
git commit -m "feat: add 5 accessibility checks"
```

---

## Task 9: Social & Conversion Checks (5 checks)

**Objective:** Implement social and conversion checks.

**Files:**
- Create: `website-grader/checks/conversion.py`

**Checks:**

| # | Check | Severity | Method |
|---|-------|----------|--------|
| 1 | Social Media Links | MEDIUM | `soup.find_all('a', href=re.compile('facebook|instagram|twitter|x.com|linkedin|youtube|tiktok'))` |
| 2 | Analytics Tracking | HIGH | Search for GA4 (`googletagmanager`/`gtag`), GTM, FB Pixel scripts |
| 3 | CTA Elements | HIGH | `soup.find_all('a', href=re.compile('contact|call|book|quote|estimate'))` + button elements with CTA text |
| 4 | Trust Signals | MEDIUM | Regex for license#, BBB, certified, bonded, insured, years in business, accreditation |
| 5 | Contact Form | MEDIUM | `soup.find('form')` with email/phone/name fields |

**Analytics detection patterns:**
```python
ANALYTICS_PATTERNS = {
    "Google Analytics 4": r'gtag\(|googletagmanager',
    "Google Tag Manager": r'googletagmanager\.com/gtm',
    "Facebook Pixel": r'connect\.facebook\.net|fbq\(',
    "Hotjar": r'hotjar',
    "Clarity": r'clarity\.ms',
}
```

**Commit:**
```bash
git add checks/conversion.py
git commit -m "feat: add 5 social/conversion checks"
```

---

## Task 10: Scoring Engine

**Objective:** Weighted scoring 0-100 across all categories.

**Files:**
- Create: `website-grader/scoring.py`
- Create: `website-grader/test_scoring.py`

**Scoring weights (sum to 100):**

| Category | Weight | Rationale |
|----------|--------|-----------|
| Technical SEO | 25 | Foundation — without this, nothing else matters |
| Local SEO | 20 | Most important for trades businesses |
| Performance | 15 | Direct ranking factor |
| Content Quality | 15 | Content is king for SEO |
| Security | 10 | Basic trust signal |
| Accessibility | 10 | Legal + UX |
| Social & Conversion | 5 | Nice to have |

**Scoring logic:**
```python
def compute_score(results: list[CheckResult]) -> dict:
    """Compute weighted score from check results."""
    category_scores = {}
    for category_name, weight in CATEGORY_WEIGHTS.items():
        cat_results = [r for r in results if r.category == category_name]
        if not cat_results:
            category_scores[category_name] = {"score": 0, "weight": weight}
            continue
        # Average score, weighted by severity
        severity_weights = {
            Severity.CRITICAL: 4, Severity.HIGH: 3,
            Severity.MEDIUM: 2, Severity.LOW: 1, Severity.INFO: 0.5
        }
        total_weight = sum(severity_weights[r.severity] for r in cat_results)
        weighted_sum = sum(r.score * severity_weights[r.severity] for r in cat_results)
        cat_score = weighted_sum / total_weight if total_weight > 0 else 0
        category_scores[category_name] = {
            "score": round(cat_score),
            "weight": weight,
            "checks_passed": sum(1 for r in cat_results if r.passed),
            "checks_total": len(cat_results),
        }

    # Overall score = sum of (category_score * category_weight / 100)
    overall = sum(cs["score"] * cs["weight"] / 100 for cs in category_scores.values())
    return {
        "overall_score": round(overall),
        "grade": score_to_grade(overall),
        "categories": category_scores,
    }

def score_to_grade(score):
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"
```

**Step 4: Run tests**
Run: `pytest test_scoring.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add scoring.py test_scoring.py
git commit -m "feat: add weighted scoring engine"
```

---

## Task 11: Fix Code Generation

**Objective:** Generate copy-pasteable fix code snippets for common issues.

**Files:**
- Create: `website-grader/fixes.py`

**Fixes to generate (all from template + extracted data, no LLM):**

| Fix | Input | Output |
|-----|-------|--------|
| LocalBusiness Schema | Extracted NAP from page | Complete JSON-LD block |
| Meta Title | Current title + domain | Optimized title suggestion |
| Meta Description | Current description + page content first 160 chars | Optimized description |
| Open Graph Tags | Page URL + title | Complete OG meta tags |
| Robots.txt | Domain | Complete robots.txt with sitemap ref |
| Sitemap.xml | Crawled page URLs | Complete sitemap.xml |
| .htaccess Security Headers | None | .htaccess snippet with security headers |
| Canonical Tag | Page URL | Canonical link tag |

**Commit:**
```bash
git add fixes.py
git commit -m "feat: add fix code generation"
```

---

## Task 12: HTML Report Generator

**Objective:** Generate a polished, self-contained HTML report that Steven can show in meetings.

**Files:**
- Create: `website-grader/report.py`
- Create: `website-grader/report_template.html`

**Report sections:**

1. **Header** — NWP branding, URL graded, date, overall score (0-100) with letter grade
2. **Executive Summary** — One-paragraph summary: "This site scores X/100. Top 3 issues: ..."
3. **Score Breakdown** — Category scores in a visual bar chart (CSS only, no JS deps)
4. **Critical Issues** — Red cards for each CRITICAL finding with fix code
5. **All Findings** — Table of all 53 checks with severity, status, and recommendation
6. **NAP Consistency Table** — For local SEO: NAP as found on each page, side by side
7. **Performance Metrics** — TTFB, page weight, compression, etc. in a table
8. **Prioritized Action Plan** — Sorted by (severity × impact / effort), top 10 fixes
9. **Fix Code Snippets** — Collapsible sections with copy-pasteable code
10. **Footer** — NWP branding, "Powered by North Web Pro"

**Design:**
- NWP brand colors: #D97548 orange, #60CFF4 blue, on #0a0a0a black
- Self-contained: all CSS inline, no external dependencies
- Printable: `@media print` styles
- Collapsible code blocks: `<details><summary>` HTML tags

**Commit:**
```bash
git add report.py report_template.html
git commit -m "feat: add HTML report generator"
```

---

## Task 13: CLI Entry Point

**Objective:** Wire everything together into a CLI tool.

**Files:**
- Create: `website-grader/grader.py`

**Usage:**
```bash
# Grade a site and open HTML report
python3 grader.py https://example.com

# Save to specific file
python3 grader.py https://example.com --output report.html

# Also save JSON
python3 grader.py https://example.com --output report.html --json report.json

# Verbose mode (print to terminal)
python3 grader.py https://example.com --verbose
```

**CLI flow:**
1. Parse args (url, --output, --json, --verbose)
2. Crawl site (show progress)
3. Run all 7 check categories (show progress)
4. Compute score
5. Generate fix snippets
6. Generate HTML report
7. Save files
8. Print summary to terminal

```python
#!/usr/bin/env python3
"""Website Grader Pro — Full audit tool for North Web Pro."""
import argparse
import sys
import time
from crawler import crawl_site
from checks import ALL_CHECK_CATEGORIES
from scoring import compute_score
from fixes import generate_fixes
from report import generate_report

def main():
    parser = argparse.ArgumentParser(description="Website Grader Pro — Full SEO Audit")
    parser.add_argument("url", help="URL to grade (e.g., https://example.com)")
    parser.add_argument("--output", "-o", default="report.html", help="Output HTML file path")
    parser.add_argument("--json", "-j", help="Also save JSON report to this path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print details to terminal")
    parser.add_argument("--max-pages", "-m", type=int, default=5, help="Max pages to crawl (default 5)")
    args = parser.parse_args()

    print(f"🔍 Grading {args.url}...")

    # 1. Crawl
    print(f"   📡 Crawling site (up to {args.max_pages} pages)...")
    crawl_result = crawl_site(args.url, max_pages=args.max_pages)
    if crawl_result.error:
        print(f"   ❌ Error: {crawl_result.error}")
        sys.exit(1)
    print(f"   ✅ Crawled {len(crawl_result.pages)} pages")

    # 2. Run checks
    all_results = []
    for CheckClass in ALL_CHECK_CATEGORIES:
        checker = CheckClass()
        print(f"   🔎 Running {checker.category_name}...")
        results = checker.run(crawl_result)
        all_results.extend(results)
        passed = sum(1 for r in results if r.passed)
        print(f"      {passed}/{len(results)} passed")

    # 3. Score
    score_data = compute_score(all_results)
    print(f"\n   📊 Overall Score: {score_data['overall_score']}/100 (Grade {score_data['grade']})")

    # 4. Fixes
    fixes = generate_fixes(crawl_result, all_results)

    # 5. Report
    html = generate_report(crawl_result, all_results, score_data, fixes, args.url)

    # 6. Save
    with open(args.output, "w") as f:
        f.write(html)
    print(f"\n   📄 Report saved to {args.output}")

    if args.json:
        import json
        report_data = {
            "url": args.url,
            "score": score_data,
            "checks": [{"check_id": r.check_id, "name": r.check_name, "category": r.category,
                       "severity": r.severity.value, "passed": r.passed, "score": r.score,
                       "detail": r.detail, "recommendation": r.recommendation,
                       "fix_code": r.fix_code, "fix_difficulty": r.fix_difficulty,
                       "impact_estimate": r.impact_estimate}
                      for r in all_results],
        }
        with open(args.json, "w") as f:
            json.dump(report_data, f, indent=2)
        print(f"   📋 JSON saved to {args.json}")

    # 7. Verbose
    if args.verbose:
        print("\n" + "="*60)
        for r in all_results:
            status = "✅" if r.passed else "❌"
            print(f"  {status} [{r.severity.value:8s}] {r.check_name}: {r.detail[:60]}")

if __name__ == "__main__":
    main()
```

**Commit:**
```bash
git add grader.py
git commit -m "feat: add CLI entry point"
```

---

## Task 14: Integration Test — Run Against a Real Site

**Objective:** Run the full pipeline against a real website and verify the report.

**Step 1: Run against a real site**
```bash
python3 grader.py https://northwebpro.com --output test_report.html --verbose
```

**Step 2: Verify report was generated**
```bash
ls -la test_report.html
# Should be > 10KB
```

**Step 3: Run against a known-bad site**
```bash
python3 grader.py http://example.com --output test_report2.html --verbose
```

**Step 4: Verify both reports have content**
- Open in browser / check for score, checks, fixes
- Verify NAP table, performance metrics, action plan present

**Step 5: Clean up test files**
```bash
rm -f test_report.html test_report2.html
git add -A
git commit -m "test: integration test against real sites"
```

---

## Phase 2 Preview (Agentic — API Key Needed)

After Phase 1 is solid, Phase 2 adds:

1. **AI Executive Summary** — LLM generates a natural-language summary: "This site is in the bottom 10% of plumbing sites I've audited. The #1 issue is..."

2. **AI Action Plan** — LLM prioritizes fixes with ROI estimates based on industry + location

3. **AI Fix Generation** — LLM generates custom meta tags, schema, and content suggestions based on the actual page content

4. **Competitive Benchmark** — Crawl 3 competitor sites, compare scores side by side

5. **Core Web Vitals** — Use CrUX API (free, needs API key) for real LCP/CLS/INP data

6. **Screenshot** — Use Playwright or similar for visual analysis (needs browser)

---

## Execution Checklist

- [ ] Task 1: Project scaffolding (base classes, registry)
- [ ] Task 2: Multi-page crawler
- [ ] Task 3: Technical SEO checks (17)
- [ ] Task 4: Performance checks (8)
- [ ] Task 5: Local SEO checks (8)
- [ ] Task 6: Content quality checks (7)
- [ ] Task 7: Security checks (3)
- [ ] Task 8: Accessibility checks (5)
- [ ] Task 9: Social & conversion checks (5)
- [ ] Task 10: Scoring engine
- [ ] Task 11: Fix code generation
- [ ] Task 12: HTML report generator
- [ ] Task 13: CLI entry point
- [ ] Task 14: Integration test

**Total: 53 checks, 7 categories, 0 API keys, 14 tasks.**