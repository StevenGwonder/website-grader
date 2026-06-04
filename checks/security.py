from .base import CheckResult, Severity, CheckCategory
from typing import List

class SecurityChecks(CheckCategory):
    category_name = "Security"
    category_weight = 10

    def run(self, crawl_result) -> List[CheckResult]:
        results = []
        if crawl_result.homepage:
            results.append(self._check_ssl(crawl_result))
            results.append(self._check_security_headers(crawl_result))
            results.append(self._check_mixed_content(crawl_result))
        return results

    def _check_ssl(self, crawl_result):
        homepage = crawl_result.homepage
        base_url = crawl_result.base_url
        passed = base_url.startswith('https://') and homepage.status_code == 200
        severity = Severity.CRITICAL
        score = 100 if passed else 0
        detail = "SSL certificate valid, site served over HTTPS" if passed else "No SSL — site is served over HTTP, browsers show 'Not Secure'"
        fix_code = "Install an SSL certificate from your hosting provider or Let's Encrypt"
        return CheckResult(
            check_id="ssl",
            check_name="SSL Certificate",
            category=self.category_name,
            severity=severity,
            passed=passed,
            score=score,
            detail=detail,
            recommendation="Serve your site over HTTPS to encrypt data and build trust",
            fix_code=fix_code,
            fix_difficulty="Medium",
            impact_estimate="High"
        )

    def _check_security_headers(self, crawl_result):
        homepage = crawl_result.homepage
        headers = homepage.headers
        required_headers = {
            'content-security-policy': Severity.HIGH,
            'strict-transport-security': Severity.HIGH,
            'x-frame-options': Severity.MEDIUM,
            'x-content-type-options': Severity.MEDIUM,
            'referrer-policy': Severity.LOW
        }
        found = [h for h in required_headers if h in headers]
        missing = [h for h in required_headers if h not in headers]
        score = int((len(found) / len(required_headers)) * 100)
        passed = score >= 60
        severity = Severity.HIGH
        detail = f"Found {len(found)} security headers: {', '.join(found)}. Missing: {', '.join(missing)}"
        fix_code = """Header always set X-Frame-Options "SAMEORIGIN"
Header always set X-Content-Type-Options "nosniff"
Header always set Strict-Transport-Security "max-age=31536000"
Header always set Referrer-Policy "strict-origin-when-cross-origin"""
        return CheckResult(
            check_id="security_headers",
            check_name="Security Headers",
            category=self.category_name,
            severity=severity,
            passed=passed,
            score=score,
            detail=detail,
            recommendation="Add missing security headers to protect against common web vulnerabilities",
            fix_code=fix_code,
            fix_difficulty="Easy",
            impact_estimate="Medium"
        )

    def _check_mixed_content(self, crawl_result):
        homepage = crawl_result.homepage
        if not homepage.url.startswith('https://'):
            return CheckResult(
                check_id="mixed_content",
                check_name="Mixed Content",
                category=self.category_name,
                severity=Severity.HIGH,
                passed=True,
                score=100,
                detail="Site is not HTTPS, mixed content check skipped",
                recommendation="Serve your site over HTTPS first",
            )

        soup = homepage.soup
        mixed = []
        if soup:
            for tag, attr in [('img', 'src'), ('script', 'src'), ('link', 'href')]:
                for element in soup.find_all(tag, attrs={attr: True}):
                    url = element[attr]
                    if url.startswith('http://'):
                        mixed.append(url)

        count = len(mixed)
        passed = count == 0
        score = 0 if count > 0 else 100
        severity = Severity.HIGH
        detail = f"Found {count} mixed content resources" if count > 0 else "No mixed content detected"
        fix_code = "Update all HTTP resource URLs to HTTPS"
        return CheckResult(
            check_id="mixed_content",
            check_name="Mixed Content",
            category=self.category_name,
            severity=severity,
            passed=passed,
            score=score,
            detail=detail,
            recommendation="Replace all HTTP resources with HTTPS versions to avoid security warnings",
            fix_code=fix_code,
            fix_difficulty="Easy",
            impact_estimate="Medium"
        )
