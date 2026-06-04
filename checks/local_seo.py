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

        homepage = crawl_result.homepage
        if homepage:
            results.append(self._check_nap_extraction(homepage))
            results.append(self._check_localbusiness_schema(homepage))
            results.append(self._check_maps_embed(homepage))
            results.append(self._check_service_area(homepage))
            results.append(self._check_city_targeting(homepage))
            results.append(self._check_review_schema(homepage))
            results.append(self._check_gbp_link(homepage))
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
        phone = phone.group() if isinstance(phone, re.Match) else None

        # Name extraction
        name = None
        try:
            ld_json = json.loads(''.join(soup.find('script', type='application/ld+json').contents))
            if isinstance(ld_json, dict) and ld_json.get('@type') == 'LocalBusiness':
                name = ld_json.get('name')
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
            names = [n["name"] for n in nap_per_page.values() if n["name"]]
            phones = [n["phone"] for n in nap_per_page.values() if n["phone"]]
            consistent = len(set(names)) <= 1 and len(set(phones)) <= 1
            if consistent:
                detail = f"NAP consistent across {len(nap_per_page)} pages"
            else:
                detail = "NAP mismatch detected across pages"
                if len(set(names)) > 1:
                    detail += " (name differs)"
                if len(set(phones)) > 1:
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

    def _check_localbusiness_schema(self, page) -> CheckResult:
        soup = page.soup
        schema_fix = '<script type="application/ld+json">{\n  "@context": "https://schema.org",\n  "@type": "LocalBusiness",\n  "name": "Your Business Name",\n  "address": {\n    "@type": "PostalAddress",\n    "streetAddress": "123 Main St",\n    "addressLocality": "City",\n    "addressRegion": "ST",\n    "postalCode": "12345"\n  },\n  "telephone": "+123****7890",\n  "geo": {\n    "@type": "GeoCoordinates",\n    "latitude": "40.7128",\n    "longitude": "-74.0060"\n  },\n  "openingHoursSpecification": [\n    {\n      "@type": "OpeningHoursSpecification",\n      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],\n      "opens": "09:00",\n      "closes": "17:00"\n    }\n  ]\n}</script>'
        if not soup:
            return CheckResult(
                check_id="local_seo_localbusiness_schema",
                check_name="LocalBusiness Schema",
                category=self.category_name,
                severity=Severity.CRITICAL,
                passed=False,
                score=0,
                detail="No LocalBusiness schema found",
                recommendation="Add LocalBusiness schema markup to your homepage.",
                fix_code=schema_fix
            )

        required_fields = ["name", "address", "telephone", "geo", "openingHoursSpecification"]
        found_fields = 0

        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    ld_json = json.loads(script.string)
                    if isinstance(ld_json, dict) and 'LocalBusiness' in str(ld_json.get('@type', '')):
                        for field in required_fields:
                            if field in ld_json:
                                found_fields += 1
                        break
                except Exception:
                    continue
        except Exception:
            pass

        score = int((found_fields / 5) * 100)
        passed = score >= 60
        detail = f"LocalBusiness schema: {found_fields}/5 required fields present"
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

    def _check_maps_embed(self, page) -> CheckResult:
        soup = page.soup
        maps_fix = '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3022.21537462995!2d-74.00597278459418!3d40.71277567933012!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x89c25a27e2f2b5e9%3A0x4d7f95e9d7f95e9d!2sYour%20Business%20Name!5e0!3m2!1sen!2sus!4v1234567890123" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>'
        if not soup:
            return CheckResult(
                check_id="local_seo_maps_embed",
                check_name="Google Maps Embed",
                category=self.category_name,
                severity=Severity.HIGH,
                passed=False,
                score=0,
                detail="No Google Maps embed found",
                recommendation="Embed a Google Map on your contact page.",
                fix_code=maps_fix
            )

        iframe = soup.find('iframe', src=True)
        passed = bool(iframe and 'google' in iframe['src'].lower() and 'maps' in iframe['src'].lower())
        score = 100 if passed else 0
        detail = "Google Maps embed found" if passed else "No Google Maps embed found"
        recommendation = "Embed a Google Map on your contact page to improve local SEO."
        return CheckResult(
            check_id="local_seo_maps_embed",
            check_name="Google Maps Embed",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=score,
            detail=detail,
            recommendation=recommendation,
            fix_code=maps_fix if not passed else None
        )

    def _check_service_area(self, page) -> CheckResult:
        soup = page.soup
        if not soup:
            return CheckResult(
                check_id="local_seo_service_area", check_name="Service Area",
                category=self.category_name, severity=Severity.HIGH,
                passed=False, score=0,
                detail="No service area information found",
                recommendation="Add service area information to your page content."
            )
        text = soup.get_text()
        patterns = [
            r'serving\s+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)',
            r'service\s+area\s+(?:includes|:)\s+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)',
            r'covering\s+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)'
        ]
        areas = []
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                areas.extend([a.strip() for a in match.group(1).split(',')])
        passed = len(areas) > 0
        detail = f"Service areas found: {', '.join(areas)}" if areas else "No service areas found"
        return CheckResult(
            check_id="local_seo_service_area", check_name="Service Area",
            category=self.category_name, severity=Severity.HIGH,
            passed=passed, score=100 if passed else 0,
            detail=detail,
            recommendation="Include service area information in your page content.",
            data={"areas": areas}
        )

    def _check_city_targeting(self, page) -> CheckResult:
        soup = page.soup
        if not soup:
            return CheckResult(
                check_id="local_seo_city_targeting", check_name="City Targeting",
                category=self.category_name, severity=Severity.HIGH,
                passed=False, score=0,
                detail="No city targeting found",
                recommendation="Include city name in title, h1, or meta description."
            )
        text = soup.get_text()
        city_match = re.search(r'\b([A-Z][a-z]+),?\s+CA\b', text)
        city = city_match.group(1) if city_match else None
        if not city:
            return CheckResult(
                check_id="local_seo_city_targeting", check_name="City Targeting",
                category=self.category_name, severity=Severity.HIGH,
                passed=False, score=0,
                detail="No city name found in page content",
                recommendation="Include city name in your page content."
            )
        title = soup.title.string if soup.title else ""
        h1 = soup.find('h1')
        h1_text = h1.get_text(strip=True) if h1 else ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_text = meta_desc.get('content', '') if meta_desc else ''
        found_in = []
        if city.lower() in title.lower(): found_in.append("title")
        if city.lower() in h1_text.lower(): found_in.append("h1")
        if city.lower() in meta_text.lower(): found_in.append("meta description")
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

    def _check_review_schema(self, page) -> CheckResult:
        soup = page.soup
        fix = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"LocalBusiness","name":"Your Business","aggregateRating":{"@type":"AggregateRating","ratingValue":"4.5","reviewCount":"100"}}</script>'
        if not soup:
            return CheckResult(
                check_id="local_seo_review_schema", check_name="Review Schema",
                category=self.category_name, severity=Severity.MEDIUM,
                passed=False, score=0,
                detail="No review schema found",
                recommendation="Add AggregateRating schema markup to your page.",
                fix_code=fix
            )
        found = False
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and ('Review' in str(data.get('@type', '')) or 'AggregateRating' in str(data.get('@type', ''))):
                    found = True
                    break
            except Exception:
                continue
        return CheckResult(
            check_id="local_seo_review_schema", check_name="Review Schema",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=found, score=100 if found else 0,
            detail="Review schema found" if found else "No review schema found",
            recommendation="Add AggregateRating schema markup to your page.",
            fix_code=fix if not found else None
        )

    def _check_gbp_link(self, page) -> CheckResult:
        soup = page.soup
        if not soup:
            return CheckResult(
                check_id="local_seo_gbp_link", check_name="Google Business Profile Link",
                category=self.category_name, severity=Severity.MEDIUM,
                passed=False, score=0,
                detail="No Google Business Profile link found",
                recommendation="Add a link to your Google Business Profile."
            )
        gbp_pattern = re.compile(r'google.*business|maps\.google|google\.com/maps', re.IGNORECASE)
        found = any(gbp_pattern.search(a['href']) for a in soup.find_all('a', href=True))
        return CheckResult(
            check_id="local_seo_gbp_link", check_name="Google Business Profile Link",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=found, score=100 if found else 0,
            detail="Google Business Profile link found" if found else "No Google Business Profile link found",
            recommendation="Add a link to your Google Business Profile on your contact page."
        )
