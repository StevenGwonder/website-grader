import re
from .base import CheckResult, Severity, CheckCategory

class ConversionChecks(CheckCategory):
    category_name = "Social & Conversion"
    category_weight = 5

    def run(self, crawl_result) -> list:
        if not crawl_result.pages:
            return []
        # Scan ALL crawled pages, not just homepage
        all_pages = [p for p in crawl_result.pages.values() if p.soup]
        results = []
        results.append(self._check_social_links(all_pages))
        results.append(self._check_analytics(crawl_result.homepage))
        results.append(self._check_cta_elements(all_pages))
        results.append(self._check_trust_signals(all_pages))
        results.append(self._check_contact_form(all_pages))
        return results

    def _check_social_links(self, pages) -> CheckResult:
        social_patterns = {
            r'facebook\.com': 'Facebook',
            r'instagram\.com': 'Instagram',
            r'twitter\.com': 'Twitter',
            r'x\.com': 'X',
            r'linkedin\.com': 'LinkedIn',
            r'youtube\.com': 'YouTube',
            r'tiktok\.com': 'TikTok',
            r'pinterest\.com': 'Pinterest',
        }
        found = []
        found_urls = []
        for page in pages:
            for a in page.soup.find_all('a', href=True):
                href = a['href'].lower()
                for pattern, platform in social_patterns.items():
                    if re.search(pattern, href) and platform not in found:
                        found.append(platform)
                        found_urls.append(f"{platform} on {page.url.split('/')[-2] or 'homepage'}")
        passed = len(found) >= 1
        detail = ", ".join(found) if found else "No social links found"
        return CheckResult(
            check_id="social_links",
            check_name="Social Media Links",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=min(100, len(found) * 25) if found else 0,
            detail=detail,
            recommendation="Add social media links to build trust and engagement." if not passed else "",
            data={"platforms": found, "locations": found_urls}
        )

    def _check_analytics(self, page) -> CheckResult:
        if not page:
            return CheckResult(
                check_id="analytics", check_name="Analytics Tools",
                category=self.category_name, severity=Severity.HIGH,
                passed=False, score=0,
                detail="No analytics tools found",
                recommendation="Install analytics to track visitor behavior and conversions.",
            )
        analytics_patterns = [
            (r'googletagmanager', 'Google Tag Manager'),
            (r'gtag\(', 'Google Analytics'),
            (r'GoogleAnalytics', 'Google Analytics'),
            (r'GA4', 'GA4'),
            (r'fbq\(', 'Facebook Pixel'),
            (r'connect\.facebook\.net', 'Facebook Pixel'),
            (r'hotjar', 'Hotjar'),
            (r'clarity\.ms', 'Microsoft Clarity'),
        ]
        found = []
        html_text = page.html.lower()
        for pattern, tool in analytics_patterns:
            if re.search(pattern.lower(), html_text) and tool not in found:
                found.append(tool)
        passed = len(found) >= 1
        detail = ", ".join(found) if found else "No analytics tools found"
        fix_code = """<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>"""
        return CheckResult(
            check_id="analytics",
            check_name="Analytics Tools",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=100 if passed else 0,
            detail=detail,
            recommendation="Install analytics to track visitor behavior and conversions." if not passed else "",
            fix_code=fix_code if not passed else None,
        )

    def _check_cta_elements(self, pages) -> CheckResult:
        cta_links = []
        seen = set()
        for page in pages:
            for a in page.soup.find_all('a', href=True):
                href = a['href'].lower()
                if re.search(r'contact|call|book|quote|estimate|schedule|appointment', href):
                    text = a.get_text(strip=True) or "Link"
                    if text not in seen:
                        cta_links.append(text)
                        seen.add(text)
            for button in page.soup.find_all('button'):
                text = button.get_text(strip=True).lower()
                if any(word in text for word in ['call', 'book', 'quote', 'contact', 'get started']):
                    full_text = button.get_text(strip=True)
                    if full_text not in seen:
                        cta_links.append(full_text)
                        seen.add(full_text)
        passed = len(cta_links) >= 1
        detail = f"Found {len(cta_links)} CTAs: {', '.join(cta_links[:5])}{'...' if len(cta_links) > 5 else ''}"
        return CheckResult(
            check_id="cta_elements",
            check_name="Call-to-Action Elements",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=100 if passed else 0,
            detail=detail,
            recommendation="Add clear call-to-action buttons/links to guide users." if not passed else "",
        )

    def _check_trust_signals(self, pages) -> CheckResult:
        trust_patterns = [
            (r'licen[sc]e', 'License'),
            (r'bonded', 'Bonded'),
            (r'insured', 'Insured'),
            (r'certified', 'Certified'),
            (r'BBB', 'BBB'),
            (r'accredited', 'Accredited'),
            (r'years in business', 'Years in Business'),
            (r'since 19\d{2}', 'Established'),
            (r'since 20\d{2}', 'Established'),
            (r'buildzoom', 'BuildZoom'),
            (r'five.?star|★★★★★|5.?star', '5-Star Reviews'),
            (r'\d+\+?\s*(?:reviews?|testimonials?)', 'Reviews'),
            (r'warranty', 'Warranty'),
            (r'guarantee', 'Guarantee'),
        ]
        found = []
        for page in pages:
            text = page.soup.get_text()
            text_lower = text.lower()
            for pattern, signal in trust_patterns:
                if re.search(pattern, text, re.IGNORECASE) and signal not in found:
                    found.append(signal)
        passed = len(found) >= 2
        score = min(100, len(found) * 20) if found else 0
        detail = ", ".join(found) if found else "No trust signals found"
        return CheckResult(
            check_id="trust_signals",
            check_name="Trust Signals",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=score,
            detail=detail,
            recommendation="Add trust signals like licenses, certifications, or years in business." if not passed else "",
        )

    def _check_contact_form(self, pages) -> CheckResult:
        """Scan ALL crawled pages for contact forms."""
        for page in pages:
            forms = page.soup.find_all('form')
            for form in forms:
                inputs = form.find_all('input')
                relevant_fields = 0
                for inp in inputs:
                    name = inp.get('name', '').lower()
                    type_ = inp.get('type', '').lower()
                    if any(kw in name for kw in ['name', 'email', 'phone', 'message']) or type_ in ['email', 'tel']:
                        relevant_fields += 1
                # Also check for textarea (message fields)
                textareas = form.find_all('textarea')
                if textareas:
                    relevant_fields += 1
                if relevant_fields >= 2:
                    short_url = page.url.replace("https://", "").replace("http://", "")[:50]
                    detail = f"Contact form found on {short_url} with {relevant_fields} fields"
                    return CheckResult(
                        check_id="contact_form",
                        check_name="Contact Form",
                        category=self.category_name,
                        severity=Severity.MEDIUM,
                        passed=True,
                        score=100,
                        detail=detail,
                        recommendation="",
                    )
        return CheckResult(
            check_id="contact_form",
            check_name="Contact Form",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=False,
            score=0,
            detail="No contact form found on any crawled page",
            recommendation="Add a contact form to make it easy for visitors to reach you.",
        )