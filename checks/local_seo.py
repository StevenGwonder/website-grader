import re
import json
from typing import Dict, List, Optional
from .base import CheckResult, Severity, CheckCategory

class LocalSeoChecks(CheckCategory):
    category_name = "Local SEO"
    category_weight = 20

    def run(self, crawl_result) -> List[CheckResult]:
        results = []
        if not crawl_result.pages:
            return results

        all_pages = [p for p in crawl_result.pages.values() if p.soup]
        homepage = crawl_result.homepage

        if homepage:
            results.append(self._check_nap_extraction(homepage))
            results.append(self._check_localbusiness_schema(all_pages))
            results.append(self._check_maps_embed(all_pages))
            results.append(self._check_service_area(all_pages))
            results.append(self._check_city_targeting(all_pages))
            results.append(self._check_review_schema(all_pages))
            results.append(self._check_gbp_link(all_pages))
        results.append(self._check_nap_consistency(crawl_result))
        return results

    def _extract_nap(self, page) -> Dict[str, Optional[str]]:
        soup = page.soup
        if not soup:
            return {"name": None, "phone": None, "address": None}

        text = soup.get_text()

        # Phone extraction
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phone = re.search(phone_pattern, text)
        if not phone:
            for a in soup.find_all('a', href=True):
                if a['href'].startswith('tel:'):
                    phone = re.search(r'tel:([\d\s\-\(\)\.]+)', a['href'])
                    if phone:
                        phone = phone.group(1)
                        break
        phone = phone.group() if isinstance(phone, re.Match) else (phone if isinstance(phone, str) else None)

        # Name extraction — prefer structured data, fall back to title
        name = None
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                ld_json = json.loads(script.string or script.get_text() or "{}")
                # Handle @graph arrays
                if isinstance(ld_json, dict):
                    graph = ld_json.get('@graph', [ld_json])
                    if isinstance(graph, dict):
                        graph = [graph]
                    for item in graph:
                        if isinstance(item, dict):
                            t = item.get('@type', '')
                            if t in ('LocalBusiness', 'Organization', 'WebSite'):
                                name = item.get('name')
                                if t in ('LocalBusiness', 'Organization'):
                                    break
                elif isinstance(ld_json, list):
                    for item in ld_json:
                        if isinstance(item, dict) and item.get('@type') in ('LocalBusiness', 'Organization'):
                            name = item.get('name')
                            break
        except Exception:
            pass
        if not name:
            name = soup.title.string if soup.title else None
        if not name:
            h1 = soup.find('h1')
            name = h1.get_text(strip=True) if h1 else None

        # Address extraction
        address_pattern = r'\d+\s+[A-Z][a-z]+\s+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Cir)\.?,?\s+([A-Z][a-z]+,?\s+[A-Z]{2}\s+\d{5})'
        address_match = re.search(address_pattern, text)
        address = address_match.group() if address_match else None

        return {"name": name, "phone": phone, "address": address}

    def _check_nap_extraction(self, page) -> CheckResult:
        nap = self._extract_nap(page)
        name, phone, address = nap["name"], nap["phone"], nap["address"]
        passed = bool(phone and name)
        score = 100 if passed else 0
        detail = f"Name: {name}, Phone: {phone}, Address: {address or 'not found'}"
        recommendation = "Ensure your business Name, Address, and Phone are clearly visible on the page."
        return CheckResult(
            check_id="local_seo_nap_extraction",
            check_name="NAP Extraction",
            category=self.category_name,
            severity=Severity.CRITICAL,
            passed=passed,
            score=score,
            detail=detail,
            recommendation=recommendation,
            data=nap
        )

    def _check_nap_consistency(self, crawl_result) -> CheckResult:
        nap_per_page = {}
        for url, page in crawl_result.pages.items():
            nap = self._extract_nap(page)
            nap_per_page[url] = nap

        if len(nap_per_page) <= 1:
            consistent = True
            detail = "NAP consistent across 1 page"
        else:
            # Normalize names for comparison — strip common suffixes
            # e.g. "Bill Barber Construction" vs "Bill Barber Construction, Home Remodeling Experts"
            # should NOT be flagged as a mismatch
            names = [n["name"] for n in nap_per_page.values() if n["name"]]
            phones = [n["phone"] for n in nap_per_page.values() if n["phone"]]

            # Normalize: take the first part before comma/separator and strip
            def normalize_name(n):
                if not n:
                    return ""
                # Split on common separators and take the base name
                for sep in [",", " - ", " | ", " — "]:
                    if sep in n:
                        return n.split(sep)[0].strip().lower()
                return n.strip().lower()

            norm_names = set(normalize_name(n) for n in names)
            # Also check if one is a prefix of another (e.g. "Bill Barber Construction" is base of "Bill Barber Construction, Home Remodeling Experts")
            names_consistent = True
            if len(norm_names) > 1:
                # Check if all names share a common base
                sorted_names = sorted(norm_names, key=len)
                shortest = sorted_names[0] if sorted_names else ""
                names_consistent = all(n.startswith(shortest) for n in sorted_names) if shortest else len(norm_names) <= 1

            phones_consistent = len(set(phones)) <= 1
            consistent = names_consistent and phones_consistent
            if consistent:
                detail = f"NAP consistent across {len(nap_per_page)} pages"
            else:
                detail = "NAP mismatch detected across pages"
                if not names_consistent:
                    detail += " (name differs)"
                if not phones_consistent:
                    detail += " (phone differs)"

        passed = consistent
        score = 100 if passed else 0
        recommendation = "Ensure NAP is identical across all pages. Use a consistent format."
        return CheckResult(
            check_id="local_seo_nap_consistency",
            check_name="NAP Consistency",
            category=self.category_name,
            severity=Severity.CRITICAL,
            passed=passed,
            score=score,
            detail=detail,
            recommendation=recommendation,
            data={"nap_per_page": nap_per_page, "consistent": consistent}
        )

    def _check_localbusiness_schema(self, pages) -> CheckResult:
        schema_fix = '<script type="application/ld+json">{\n  "@context": "https://schema.org",\n  "@type": "LocalBusiness",\n  "name": "Your Business Name",\n  "address": {\n    "@type": "PostalAddress",\n    "streetAddress": "123 Main St",\n    "addressLocality": "City",\n    "addressRegion": "ST",\n    "postalCode": "12345"\n  },\n  "telephone": "+1234567890",\n  "geo": {\n    "@type": "GeoCoordinates",\n    "latitude": "40.7128",\n    "longitude": "-74.0060"\n  },\n  "openingHoursSpecification": [\n    {\n      "@type": "OpeningHoursSpecification",\n      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],\n      "opens": "09:00",\n      "closes": "17:00"\n    }\n  ]\n}</script>'
        required_fields = ["name", "address", "telephone", "geo", "openingHoursSpecification"]
        found_fields = 0
        found_on_page = ""

        for page in pages:
            scripts = page.soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    raw = script.string or script.get_text() or "{}"
                    ld_json = json.loads(raw)
                    # Handle @graph arrays
                    items = []
                    if isinstance(ld_json, dict):
                        if '@graph' in ld_json:
                            items = ld_json['@graph'] if isinstance(ld_json['@graph'], list) else [ld_json['@graph']]
                        else:
                            items = [ld_json]
                    elif isinstance(ld_json, list):
                        items = ld_json

                    for item in items:
                        if isinstance(item, dict):
                            t = str(item.get('@type', ''))
                            if 'LocalBusiness' in t or 'Organization' in t:
                                for field in required_fields:
                                    if field in item:
                                        found_fields += 1
                                found_on_page = page.url.split("/")[-2] or "homepage"
                                break
                    if found_fields > 0:
                        break
                except (json.JSONDecodeError, TypeError):
                    continue
            if found_fields > 0:
                break

        score = int((found_fields / 5) * 100)
        passed = score >= 60
        detail = f"LocalBusiness schema: {found_fields}/5 required fields present" + (f" (found on {found_on_page})" if found_on_page else "")
        recommendation = "Add complete LocalBusiness schema with all required fields."
        return CheckResult(
            check_id="local_seo_localbusiness_schema",
            check_name="LocalBusiness Schema",
            category=self.category_name,
            severity=Severity.CRITICAL,
            passed=passed,
            score=score,
            detail=detail,
            recommendation=recommendation,
            fix_code=schema_fix if not passed else None
        )

    def _check_maps_embed(self, pages) -> CheckResult:
        """Scan ALL crawled pages for Google Maps embed."""
        maps_fix = '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3022.21537462995!2d-74.00597278459418!3d40.71277567933012!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x89c25a27e2f2b5e9%3A0x4d7f95e9d7f95e9d!2sYour%20Business%20Name!5e0!3m2!1sen!2sus!4v1234567890123" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>'
        for page in pages:
            iframes = page.soup.find_all('iframe', src=True)
            for iframe in iframes:
                src = iframe['src'].lower()
                if 'google' in src and 'maps' in src:
                    short_url = page.url.replace("https://", "").replace("http://", "")[:50]
                    return CheckResult(
                        check_id="local_seo_maps_embed",
                        check_name="Google Maps Embed",
                        category=self.category_name,
                        severity=Severity.HIGH,
                        passed=True,
                        score=100,
                        detail=f"Google Maps embed found on {short_url}",
                        recommendation="",
                    )
        return CheckResult(
            check_id="local_seo_maps_embed",
            check_name="Google Maps Embed",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=False,
            score=0,
            detail="No Google Maps embed found on any crawled page",
            recommendation="Embed a Google Map on your contact page to improve local SEO.",
            fix_code=maps_fix
        )

    def _check_service_area(self, pages) -> CheckResult:
        """Scan ALL crawled pages for service area mentions."""
        patterns = [
            r'serving\s+([A-Z][A-Za-z\s,]+?)(?:[.\n]|\s+and\s)',
            r'service\s+area\s*(?:includes|:)?\s*([A-Z][A-Za-z\s,]+?)(?:[.\n]|\s+and\s)',
            r'covering\s+([A-Z][A-Za-z\s,]+?)(?:[.\n]|\s+and\s)',
            r'areas?\s+we\s+serve:?\s*([A-Z][A-Za-z\s,]+?)(?:[.\n]|$)',
            r'located\s+in\s+([A-Z][A-Za-z\s,]+?)(?:[.\n]|\s+and\s)',
            r'based\s+in\s+([A-Z][A-Za-z\s,]+?)(?:[.\n]|\s+and\s)',
        ]
        areas = []
        for page in pages:
            text = page.soup.get_text()
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    for area in match.split(','):
                        area = area.strip()
                        if area and area not in areas and len(area) < 50:
                            areas.append(area)
            # Also look for common city patterns with state abbreviation
            city_state = re.findall(r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*,?\s+(?:CA|TX|NY|FL|WA|OR|AZ|NV|CO)\b', text)
            for cs in city_state:
                if cs not in areas and len(cs) < 50:
                    areas.append(cs)
        passed = len(areas) > 0
        detail = f"Service areas found: {', '.join(areas[:10])}" if areas else "No service areas found"
        return CheckResult(
            check_id="local_seo_service_area", check_name="Service Area",
            category=self.category_name, severity=Severity.HIGH,
            passed=passed, score=min(100, len(areas) * 25) if passed else 0,
            detail=detail,
            recommendation="Include service area information in your page content.",
            data={"areas": areas}
        )

    def _check_city_targeting(self, pages) -> CheckResult:
        """Scan ALL crawled pages for city targeting — support multi-word city names."""
        # First, try to detect city name from page content (look for "City, ST" patterns)
        all_text = ""
        for page in pages:
            all_text += page.soup.get_text() + "\n"

        # Look for multi-word city names followed by state abbrev
        city_state_match = re.search(r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s*,?\s+(?:CA|TX|NY|FL|WA|OR|AZ|NV|CO)\b', all_text)
        city = city_state_match.group(1) if city_state_match else None

        if not city:
            return CheckResult(
                check_id="local_seo_city_targeting", check_name="City Targeting",
                category=self.category_name, severity=Severity.HIGH,
                passed=False, score=0,
                detail="No city name found in page content",
                recommendation="Include city name in your page content."
            )

        # Check if the full city name (e.g. "San Marcos") appears in title, h1, or meta description
        found_in = []
        for page in pages:
            title = page.soup.title.string if page.soup.title else ""
            h1 = page.soup.find('h1')
            h1_text = h1.get_text(strip=True) if h1 else ""
            meta_desc = page.soup.find('meta', attrs={'name': 'description'})
            meta_text = meta_desc.get('content', '') if meta_desc else ''
            if city.lower() in title.lower() and "title" not in found_in:
                found_in.append("title")
            if city.lower() in h1_text.lower() and "h1" not in found_in:
                found_in.append("h1")
            if city.lower() in meta_text.lower() and "meta description" not in found_in:
                found_in.append("meta description")

        passed = len(found_in) > 0
        detail = f"City '{city}' found in: {', '.join(found_in)}" if found_in else f"City '{city}' not found in title, h1, or meta description"
        return CheckResult(
            check_id="local_seo_city_targeting", check_name="City Targeting",
            category=self.category_name, severity=Severity.HIGH,
            passed=passed, score=100 if passed else 0,
            detail=detail,
            recommendation="Include city name in title, h1, or meta description for better local SEO.",
            data={"city": city, "found_in": found_in}
        )

    def _check_review_schema(self, pages) -> CheckResult:
        """Scan ALL crawled pages for review schema AND visible review signals."""
        fix = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"LocalBusiness","name":"Your Business","aggregateRating":{"@type":"AggregateRating","ratingValue":"4.5","reviewCount":"100"}}</script>'
        found_schema = False
        found_visible = False
        visible_signals = []

        for page in pages:
            # Check JSON-LD for Review or AggregateRating
            for script in page.soup.find_all('script', type='application/ld+json'):
                try:
                    raw = script.string or script.get_text() or ""
                    data = json.loads(raw)
                    items = []
                    if isinstance(data, dict):
                        if '@graph' in data:
                            items = data['@graph'] if isinstance(data['@graph'], list) else [data['@graph']]
                        else:
                            items = [data]
                    elif isinstance(data, list):
                        items = data
                    for item in items:
                        if isinstance(item, dict):
                            t = str(item.get('@type', ''))
                            if 'Review' in t or 'AggregateRating' in str(item):
                                found_schema = True
                                break
                except (json.JSONDecodeError, TypeError):
                    continue
            if found_schema:
                break

        # Also check for visible review signals (text on page)
        for page in pages:
            text = page.soup.get_text().lower()
            if re.search(r'\d+\+?\s*(?:five.?star|★★★★★)|5.?star', text, re.IGNORECASE):
                found_visible = True
                visible_signals.append("star reviews text")
            if re.search(r'buildzoom\s+score\s*:?\s*\d+', text):
                found_visible = True
                visible_signals.append("BuildZoom score")
            if re.search(r'\d+\+?\s*reviews?', text):
                found_visible = True
                visible_signals.append("review count")

        if found_schema:
            return CheckResult(
                check_id="local_seo_review_schema", check_name="Review Schema",
                category=self.category_name, severity=Severity.MEDIUM,
                passed=True, score=100,
                detail="Review schema found",
                recommendation="",
            )
        elif found_visible:
            return CheckResult(
                check_id="local_seo_review_schema", check_name="Review Schema",
                category=self.category_name, severity=Severity.MEDIUM,
                passed=False, score=40,
                detail=f"Review signals found on page ({', '.join(set(visible_signals))}) but no schema markup",
                recommendation="Add AggregateRating schema markup to your page for rich snippets.",
                fix_code=fix
            )
        return CheckResult(
            check_id="local_seo_review_schema", check_name="Review Schema",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=False, score=0,
            detail="No review schema found",
            recommendation="Add AggregateRating schema markup to your page.",
            fix_code=fix
        )

    def _check_gbp_link(self, pages) -> CheckResult:
        """Scan ALL crawled pages for Google Business Profile link."""
        gbp_pattern = re.compile(r'google.*business|maps\.google|google\.com/maps|business\.google', re.IGNORECASE)
        for page in pages:
            for a in page.soup.find_all('a', href=True):
                if gbp_pattern.search(a['href']):
                    return CheckResult(
                        check_id="local_seo_gbp_link", check_name="Google Business Profile Link",
                        category=self.category_name, severity=Severity.MEDIUM,
                        passed=True, score=100,
                        detail="Google Business Profile link found",
                        recommendation="",
                    )
        return CheckResult(
            check_id="local_seo_gbp_link", check_name="Google Business Profile Link",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=False, score=0,
            detail="No Google Business Profile link found on any crawled page",
            recommendation="Add a link to your Google Business Profile on your contact page."
        )