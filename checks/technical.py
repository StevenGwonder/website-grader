"""17 Technical SEO checks — all programmable, no API keys."""
import re
import json
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

from curl_cffi import requests as req
from bs4 import BeautifulSoup

from .base import CheckResult, Severity, CheckCategory

def classify_link_outcome(status_code, error_str) -> str:
    if error_str:
        err = error_str.lower()
        if "timeout" in err or "timed out" in err or "timedout" in err or "deadline" in err:
            return "timeout"
        if "dns" in err or "name resolution" in err or "resolve" in err or "not known" in err:
            return "dns_error"
        if "ssl" in err or "tls" in err or "cert" in err or "handshake" in err:
            return "tls_failure"
        return "unverified_destination"
    if status_code is not None:
        if status_code == 403:
            return "access_restricted"
        if status_code == 429:
            return "rate_limited"
        if status_code >= 400:
            return "broken"
        return "valid"
    return "unverified_destination"

class TechnicalChecks(CheckCategory):
    category_name = "Technical SEO"
    category_weight = 25  # 25% of overall score

    def run(self, crawl_result) -> list[CheckResult]:
        results = []
        homepage = crawl_result.homepage
        if not homepage or not homepage.soup:
            return results

        results.append(self._check_meta_title(homepage))
        results.append(self._check_tech_meta_desc(homepage))
        results.append(self._check_tech_headings(homepage))
        results.append(self._check_canonical(homepage))
        results.append(self._check_robots_meta(homepage))
        results.append(self._check_schema(homepage))
        results.append(self._check_tech_og_tags(homepage))
        results.append(self._check_twitter_cards(homepage))
        results.append(self._check_favicon(homepage))
        results.append(self._check_sitemap(crawl_result))
        results.append(self._check_robots_txt(crawl_result))
        results.append(self._check_broken_links(crawl_result))
        results.append(self._check_tech_redirects(crawl_result))
        results.append(self._check_internal_links(crawl_result))
        results.append(self._check_url_structure(crawl_result))
        results.append(self._check_pagination(homepage))
        results.append(self._check_breadcrumbs(homepage))

        # Inject raw-vs-rendered disparities into the relevant CheckResults
        disparities = getattr(homepage, "raw_vs_rendered_disparities", {})
        if disparities:
            for r in results:
                if r.check_id == "tech_meta_title" and "title" in disparities:
                    r.data["raw_vs_rendered_disparity"] = disparities["title"]
                elif r.check_id == "tech_canonical" and "canonical" in disparities:
                    r.data["raw_vs_rendered_disparity"] = disparities["canonical"]
                elif r.check_id == "tech_robots_meta" and "robots" in disparities:
                    r.data["raw_vs_rendered_disparity"] = disparities["robots"]
                elif r.check_id == "tech_headings" and "headings" in disparities:
                    r.data["raw_vs_rendered_disparity"] = disparities["headings"]
                elif r.check_id == "tech_schema" and "structured_data" in disparities:
                    r.data["raw_vs_rendered_disparity"] = disparities["structured_data"]

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

    def _check_tech_meta_desc(self, page):
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

    def _check_tech_headings(self, page):
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
        return json.dumps({
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": "Your Business Name",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "Your Address",
                "addressLocality": "Your City",
                "addressRegion": "Your State",
                "postalCode": "Your Zip Code",
                "addressCountry": "US"
            },
            "telephone": "Your Phone Number",
            "openingHoursSpecification": [{
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
                "opens": "09:00",
                "closes": "17:00"
            }],
            "url": page.final_url
        }, indent=2)

    def _check_tech_og_tags(self, page):
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
        
        # Detect if it's a sitemap index file
        is_index = False
        if has_sitemap and ("<sitemapindex" in crawl_result.sitemap_xml.lower()):
            is_index = True

        passed = has_sitemap and (url_count > 0 or is_index)
        
        detail = ""
        if has_sitemap:
            if is_index:
                detail = f"Sitemap index found with {url_count} parsed child URLs"
            else:
                detail = f"Sitemap found with {url_count} URLs"
        else:
            detail = "No sitemap.xml found"

        return CheckResult(
            check_id="tech_sitemap",
            check_name="XML Sitemap",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=100 if passed else 0,
            detail=detail,
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
        external_outcomes = {}
        for link in all_links:
            is_internal = urlparse(link).netloc == crawl_result.base_domain
            status = None
            error_str = None
            try:
                resp = req.get(link, timeout=5, stream=True, allow_redirects=True, impersonate="chrome")
                status = resp.status_code
            except Exception as e:
                error_str = str(e)
                
            classification = classify_link_outcome(status, error_str)
            
            if not is_internal:
                external_outcomes[link] = classification
                if classification == "broken":
                    broken.append({"url": link, "status": status or "error"})
            else:
                if classification == "broken" or status is None:
                    broken.append({"url": link, "status": status or "error"})

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
            data={
                "total_links": len(all_links),
                "broken_links": broken,
                "external_link_outcomes": external_outcomes
            },
        )

    def _check_tech_redirects(self, crawl_result):
        chains = []
        for url, page in crawl_result.pages.items():
            hops = getattr(page, "redirect_hops", [])
            redirect_type = getattr(page, "redirect_type", None)
            is_chain = (redirect_type in ("redirect_chain", "loop")) or (len(hops) > 2)
            if is_chain:
                chains.append({
                    "from": url,
                    "to": page.final_url,
                    "hops": hops,
                    "type": redirect_type or "redirect_chain"
                })
        passed = len(chains) == 0
        return CheckResult(
            check_id="tech_redirects",
            check_name="Redirect Chains",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=100 if passed else 50,
            detail=f"Found {len(chains)} redirect chains/loops" if chains else "No redirect chains detected",
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
