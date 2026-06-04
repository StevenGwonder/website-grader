import re
from .base import CheckResult, Severity, CheckCategory

class ConversionChecks(CheckCategory):
    category_name = "Social & Conversion"
    category_weight = 5

    def run(self, crawl_result) -> list:
        page = crawl_result.homepage
        if not page or not page.soup:
            return []
        results = []
        results.append(self._check_social_links(page))
        results.append(self._check_analytics(page))
        results.append(self._check_cta_elements(page))
        results.append(self._check_trust_signals(page))
        results.append(self._check_contact_form(page))
        return results

    def _check_social_links(self, page) -> CheckResult:
        social_patterns = [
            r'facebook\.com', r'instagram\.com', r'twitter\.com', r'x\.com',
            r'linkedin\.com', r'youtube\.com', r'tiktok\.com'
        ]
        found = []
        for a in page.soup.find_all('a', href=True):
            href = a['href'].lower()
            for pattern in social_patterns:
                if re.search(pattern, href):
                    platform = pattern.split('.')[0].title()
                    if platform not in found:
                        found.append(platform)
        passed = len(found) >= 1
        detail = ", ".join(found) if found else "No social links found"
        return CheckResult(
            check_id="social_links",
            check_name="Social Media Links",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=2 if passed else 0,
            detail=detail,
            recommendation="Add social media links to build trust and engagement.",
            fix_code=None,
            fix_difficulty="Easy",
            impact_estimate="Low"
        )

    def _check_analytics(self, page) -> CheckResult:
        analytics_patterns = [
            r'googletagmanager', r'gtag\(', r'GoogleAnalytics', r'GA4',
            r'fbq\(', r'connect\.facebook\.net', r'hotjar', r'clarity\.ms'
        ]
        found = []
        html_text = page.html.lower()
        for pattern in analytics_patterns:
            if re.search(pattern, html_text):
                tool = pattern.split('.')[0].title()
                if tool not in found:
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
            score=3 if passed else 0,
            detail=detail,
            recommendation="Install analytics to track visitor behavior and conversions.",
            fix_code=fix_code,
            fix_difficulty="Easy",
            impact_estimate="High"
        )

    def _check_cta_elements(self, page) -> CheckResult:
        cta_links = []
        for a in page.soup.find_all('a', href=True):
            href = a['href'].lower()
            if re.search(r'contact|call|book|quote|estimate|schedule|appointment', href):
                text = a.get_text(strip=True) or "Link"
                cta_links.append(text)
        for button in page.soup.find_all('button'):
            text = button.get_text(strip=True).lower()
            if any(word in text for word in ['call', 'book', 'quote', 'contact', 'get started']):
                cta_links.append(button.get_text(strip=True))
        passed = len(cta_links) >= 1
        detail = f"Found {len(cta_links)} CTAs: {', '.join(cta_links[:5])}{'...' if len(cta_links) > 5 else ''}"
        return CheckResult(
            check_id="cta_elements",
            check_name="Call-to-Action Elements",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=3 if passed else 0,
            detail=detail,
            recommendation="Add clear call-to-action buttons/links to guide users.",
            fix_code=None,
            fix_difficulty="Easy",
            impact_estimate="High"
        )

    def _check_trust_signals(self, page) -> CheckResult:
        trust_patterns = [
            r'license', r'bonded', r'insured', r'certified',
            r'BBB', r'accredited', r'years in business',
            r'since 19\d{2}', r'established'
        ]
        found = []
        text = page.soup.get_text().lower()
        for pattern in trust_patterns:
            if re.search(pattern, text):
                signal = pattern.split('|')[0].title()
                if signal not in found:
                    found.append(signal)
        passed = len(found) >= 2
        detail = ", ".join(found) if found else "No trust signals found"
        return CheckResult(
            check_id="trust_signals",
            check_name="Trust Signals",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=2 if passed else 0,
            detail=detail,
            recommendation="Add trust signals like licenses, certifications, or years in business.",
            fix_code=None,
            fix_difficulty="Easy",
            impact_estimate="Medium"
        )

    def _check_contact_form(self, page) -> CheckResult:
        forms = page.soup.find_all('form')
        for form in forms:
            inputs = form.find_all('input')
            relevant_fields = 0
            for inp in inputs:
                name = inp.get('name', '').lower()
                type_ = inp.get('type', '').lower()
                if any(kw in name for kw in ['name', 'email', 'phone']) or type_ in ['email', 'tel']:
                    relevant_fields += 1
            if relevant_fields >= 2:
                detail = f"Contact form found with {relevant_fields} fields"
                return CheckResult(
                    check_id="contact_form",
                    check_name="Contact Form",
                    category=self.category_name,
                    severity=Severity.MEDIUM,
                    passed=True,
                    score=2,
                    detail=detail,
                    recommendation="Keep your contact form simple and accessible.",
                    fix_code=None,
                    fix_difficulty="Easy",
                    impact_estimate="Medium"
                )
        return CheckResult(
            check_id="contact_form",
            check_name="Contact Form",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=False,
            score=0,
            detail="No contact form found",
            recommendation="Add a contact form to make it easy for visitors to reach you.",
            fix_code=None,
            fix_difficulty="Easy",
            impact_estimate="Medium"
        )
