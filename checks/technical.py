"""17 Technical SEO checks — all programmable, no API keys."""
import re
import json
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

from curl_cffi import requests as req
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
        """Check schema/structured data — parse @graph, partial scoring for valid schema types."""
        schemas = page.soup.find_all("script", type="application/ld+json")
        schema_types = []
        valid_schemas = []
        for s in schemas:
            try:
                data = json.loads(s.string or s.get_text() or "{}")
                if isinstance(data, list):
                    for item in data:
                        t = item.get("@type", "") if isinstance(item, dict) else ""
                        schema_types.append(t)
                        valid_schemas.append(item)
                elif isinstance(data, dict):
                    # Handle @graph arrays (Yoast SEO pattern)
                    if "@graph" in data:
                        graph = data["@graph"]
                        if isinstance(graph, list):
                            for item in graph:
                                if isinstance(item, dict):
                                    t = item.get("@type", "")
                                    schema_types.append(t)
                                    valid_schemas.append(item)
                        elif isinstance(graph, dict):
                            t = graph.get("@type", "")
                            schema_types.append(t)
                            valid_schemas.append(graph)
                    else:
                        t = data.get("@type", "")
                        schema_types.append(t)
                        valid_schemas.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

        has_local_business = any("LocalBusiness" in str(t) for t in schema_types)
        has_organization = any("Organization" in str(t) for t in schema_types)
        has_faq = any("FAQPage" in str(t) for t in schema_types)
        has_breadcrumb = any("BreadcrumbList" in str(t) for t in schema_types)
        has_webpage = any("WebPage" in str(t) for t in schema_types)
        has_website = any("WebSite" in str(t) for t in schema_types)
        has_image = any("ImageObject" in str(t) for t in schema_types)

        # Partial scoring — credit for having any valid schema
        score = 0
        if has_local_business: score += 50
        if has_organization: score += 15
        if has_faq: score += 15
        if has_breadcrumb: score += 10
        if has_webpage: score += 5
        if has_website: score += 5
        if has_image: score += 5
        # Cap at 100
        score = min(100, score)
        if not schemas: score = 0

        passed = score >= 50  # At least has LocalBusiness or equivalent

        types_str = ", ".join(t for t in schema_types if t) if schema_types else "none"
        return CheckResult(
            check_id="tech_schema",
            check_name="Schema / Structured Data",
            category=self.category_name,
            severity=Severity.CRITICAL,
            passed=passed,
            score=score,
            detail=f"Found {len(schemas)} schema blocks: {types_str}",
            recommendation="Add LocalBusiness schema with name, address, phone, geo, and hours. Add FAQ schema for FAQ sections. Use Google's Rich Results Test to validate." if not has_local_business else "",
            fix_code=self._generate_local_business_schema(page) if not has_local_business else None,
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
        base_domain = crawl_result.base_domain
        for link in all_links:
            try:
                resp = req.head(link, timeout=5, allow_redirects=True, impersonate="chrome")
                status = resp.status_code
                link_domain = urlparse(link).netloc
                is_internal = link_domain == base_domain or link_domain == "www." + base_domain or base_domain == "www." + link_domain
                if is_internal:
                    if status != 200:
                        broken.append({"url": link, "status": status})
                else:
                    if status == 404 or status >= 500:
                        broken.append({"url": link, "status": status})
            except Exception:
                broken.append({"url": link, "status": "error"})

        count = len(broken)
        if count == 0:
            score = 100
        elif count <= 2:
            score = 80
        else:
            score = max(0, 100 - count * 20)
        passed = count == 0

        if not all_links:
            detail = "No links found to check"
        elif count == 0:
            detail = f"Checked {len(all_links)} links, no broken links found"
        else:
            urls = ", ".join(b["url"] for b in broken[:5])
            detail = f"Checked {len(all_links)} links, found {count} broken: {urls}"

        return CheckResult(
            check_id="tech_broken_links",
            check_name="Broken Links",
            category=self.category_name,
            severity=Severity.CRITICAL,
            passed=passed,
            score=score,
            detail=detail,
            recommendation=f"Fix {count} broken links. These hurt UX and SEO." if broken else "",
            fix_code="\n".join([f"<!-- Fix: {b['url']} returned {b['status']} -->" for b in broken[:5]]),
            fix_difficulty="Medium (varies)",
            impact_estimate="Critical — broken links hurt user experience and crawl budget",
            data={"total_links": len(all_links), "broken_links": broken},
        )

    def _check_redirect_chains(self, crawl_result):
        def is_standard_redirect(url, final_url):
            # http -> https
            if url.startswith("http://") and final_url.startswith("https://"):
                rest_u = url[7:]
                rest_f = final_url[8:]
                if rest_u == rest_f:
                    return True
            # www -> non-www (or vice versa)
            for u, f in [(url, final_url), (final_url, url)]:
                parsed_u = urlparse(u)
                parsed_f = urlparse(f)
                host_u = parsed_u.netloc
                host_f = parsed_f.netloc
                path_u = parsed_u.path
                path_f = parsed_f.path
                if path_u == path_f and host_u.replace("www.", "", 1) == host_f.replace("www.", "", 1):
                    if ("www." + host_u == host_f) or ("www." + host_f == host_u):
                        return True
            # sitemap.xml -> sitemap_index.xml
            if url.endswith("/sitemap.xml") and final_url.endswith("/sitemap_index.xml"):
                return True
            return False

        problematic = []
        for url, page in crawl_result.pages.items():
            if page.final_url and page.final_url != url:
                if not is_standard_redirect(url, page.final_url):
                    problematic.append({"from": url, "to": page.final_url})

        passed = len(problematic) == 0
        return CheckResult(
            check_id="tech_redirects",
            check_name="Redirect Chains",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=100 if passed else 50,
            detail=f"Found {len(problematic)} non-standard redirects" if problematic else "No problematic redirect chains detected",
            recommendation="Minimize non-standard redirects. Each redirect adds latency. Direct links are better than chains." if not passed else "",
            fix_difficulty="Medium",
            impact_estimate="Medium — redirect chains add latency and dilute link equity",
            data={"redirects": problematic},
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
        # Pagination is optional — informational only, always passes
        if has_pagination:
            score = 100
            detail = f"Pagination tags: next={'yes' if next_link else 'no'}, prev={'yes' if prev_link else 'no'}"
            recommendation = ""
        else:
            score = 100  # No pagination needed — not penalized
            detail = "No pagination tags (not required for most sites)"
            recommendation = "If you have multi-page content (blog, portfolio), add rel=next/prev tags."
        return CheckResult(
            check_id="tech_pagination",
            check_name="Pagination Tags",
            category=self.category_name,
            severity=Severity.LOW,
            passed=True,  # Always passes — informational
            score=score,
            detail=detail,
            recommendation=recommendation,
            data={"has_next": bool(next_link), "has_prev": bool(prev_link)},
        )

    def _check_breadcrumbs(self, page):
        breadcrumb_html = page.soup.find(class_=re.compile(r"breadcrumb", re.I))
        # Also check for BreadcrumbList schema (including @graph)
        schemas = page.soup.find_all("script", type="application/ld+json")
        has_breadcrumb_schema = False
        for s in schemas:
            try:
                data = json.loads(s.string or s.get_text() or "{}")
                items = []
                if isinstance(data, dict):
                    if "@graph" in data:
                        graph = data["@graph"]
                        items = graph if isinstance(graph, list) else [graph]
                    else:
                        items = [data]
                elif isinstance(data, list):
                    items = data
                for item in items:
                    if isinstance(item, dict) and "BreadcrumbList" in str(item.get("@type", "")):
                        has_breadcrumb_schema = True
                        break
            except (json.JSONDecodeError, TypeError):
                pass
            if has_breadcrumb_schema:
                break
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
