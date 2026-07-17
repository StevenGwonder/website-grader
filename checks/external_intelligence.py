"""External Intelligence checks — free APIs, no API keys required."""
import json
import re
from urllib.parse import urlparse
from datetime import datetime, timezone
from curl_cffi import requests as req
from .base import CheckResult, Severity, CheckCategory


class ExternalIntelligenceChecks(CheckCategory):
    category_name = "External Intelligence"
    category_weight = 5  # 5% — supplementary, not core

    def _safe_check(self, check_id, check_name, severity, fn, *args, **kwargs):
        """Wrap a check function with standard try/except/return-CheckResult boilerplate.
        
        The fn should return a CheckResult on success. On exception, this returns
        a safe INFO/passed=True result.
        """
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return CheckResult(
                check_id=check_id,
                check_name=check_name,
                category=self.category_name,
                severity=Severity.INFO,
                passed=True,
                score=100,
                detail=f"{check_name} unavailable: {e}",
                recommendation="",
                data={"error": str(e)},
            )

    def run(self, crawl_result) -> list:
        results = []
        base_url = crawl_result.base_url
        domain = urlparse(base_url).netloc

        results.append(self._check_mozilla_observatory(domain))
        results.append(self._check_crt_sh(domain))
        results.append(self._check_hsts_preload(domain))
        results.append(self._check_wappalyzer(crawl_result))
        results.append(self._check_whois(domain))
        return results

    def _check_mozilla_observatory(self, domain: str) -> CheckResult:
        """Check security headers via Mozilla Observatory free API."""
        def _run():
            resp = req.get(
                f"https://observatory-api.mdn.mozilla.net/api/v2/scan?host={domain}",
                timeout=15,
                impersonate="chrome",
            )
            if resp.status_code == 200:
                data = resp.json()
                score = data.get("score", 0)
                grade = data.get("grade", "F")
                tests_passed = data.get("tests_passed", 0)
                tests_total = data.get("tests_total", 0)

                passed = score >= 50
                detail = f"Mozilla Observatory: Grade {grade}, Score {score}/100 ({tests_passed}/{tests_total} tests passed)"
                recommendation = ""
                if not passed:
                    recommendation = f"Improve security headers. Current grade: {grade}. See https://observatory.mozilla.org/analyze/{domain} for details."

                return CheckResult(
                    check_id="ext_mozilla_observatory",
                    check_name="Mozilla Observatory (Security Headers)",
                    category=self.category_name,
                    severity=Severity.HIGH,
                    passed=passed,
                    score=score,
                    detail=detail,
                    recommendation=recommendation,
                    fix_difficulty="Medium",
                    impact_estimate="High — security headers protect against XSS, clickjacking, and data leaks",
                    data={"grade": grade, "score": score, "tests_passed": tests_passed, "tests_total": tests_total},
                )
            else:
                return CheckResult(
                    check_id="ext_mozilla_observatory",
                    check_name="Mozilla Observatory (Security Headers)",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=True,
                    score=100,
                    detail=f"Mozilla Observatory API returned HTTP {resp.status_code} — check skipped",
                    recommendation="",
                    data={"status_code": resp.status_code},
                )

        return self._safe_check(
            "ext_mozilla_observatory",
            "Mozilla Observatory (Security Headers)",
            Severity.HIGH,
            _run,
        )

    def _check_crt_sh(self, domain: str) -> CheckResult:
        """Check SSL certificate history via crt.sh free API."""
        def _run():
            # Strip port and www prefix for crt.sh lookup
            clean_domain = domain.split(":")[0]
            if clean_domain.startswith("www."):
                clean_domain = clean_domain[4:]

            resp = req.get(
                f"https://crt.sh/?q={clean_domain}&output=json",
                timeout=15,
                impersonate="chrome",
            )
            if resp.status_code == 200:
                try:
                    certs = resp.json()
                except (json.JSONDecodeError, TypeError):
                    certs = []

                if isinstance(certs, list) and len(certs) > 0:
                    # Get unique issuers
                    issuers = set()
                    for c in certs[:20]:
                        issuer = c.get("issuer_name", "")
                        if issuer:
                            issuers.add(issuer)

                    # Check if any certs are expired
                    import datetime
                    now = datetime.datetime.now(datetime.timezone.utc)
                    expired = 0
                    valid = 0
                    for c in certs[:50]:
                        not_after = c.get("not_after", "")
                        if not_after:
                            try:
                                expiry = datetime.datetime.strptime(not_after, "%Y-%m-%dT%H:%M:%S")
                                expiry = expiry.replace(tzinfo=datetime.timezone.utc)
                                if expiry < now:
                                    expired += 1
                                else:
                                    valid += 1
                            except (ValueError, TypeError):
                                pass

                    passed = valid > 0
                    detail = f"crt.sh: {len(certs)} certificates found, {valid} valid, {expired} expired"
                    if issuers:
                        detail += f". Issuers: {', '.join(list(issuers)[:3])}"

                    return CheckResult(
                        check_id="ext_crt_sh",
                        check_name="SSL Certificate History (crt.sh)",
                        category=self.category_name,
                        severity=Severity.MEDIUM,
                        passed=passed,
                        score=100 if passed else 0,
                        detail=detail,
                        recommendation="Ensure SSL certificates are valid and not expired." if not passed else "",
                        data={"total_certs": len(certs), "valid": valid, "expired": expired},
                    )
                else:
                    return CheckResult(
                        check_id="ext_crt_sh",
                        check_name="SSL Certificate History (crt.sh)",
                        category=self.category_name,
                        severity=Severity.INFO,
                        passed=True,
                        score=100,
                        detail="crt.sh: No certificates found for this domain",
                        recommendation="",
                        data={"total_certs": 0},
                    )
            else:
                return CheckResult(
                    check_id="ext_crt_sh",
                    check_name="SSL Certificate History (crt.sh)",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=True,
                    score=100,
                    detail=f"crt.sh API returned HTTP {resp.status_code} — check skipped",
                    recommendation="",
                )

        return self._safe_check(
            "ext_crt_sh",
            "SSL Certificate History (crt.sh)",
            Severity.MEDIUM,
            _run,
        )

    def _check_hsts_preload(self, domain: str) -> CheckResult:
        """Check if domain is in Chrome's HSTS preload list."""
        def _run():
            clean_domain = domain.split(":")[0]
            resp = req.get(
                f"https://hstspreload.org/api/v2/status?domain={clean_domain}",
                timeout=10,
                impersonate="chrome",
            )
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "unknown")
                passed = status == "preloaded"
                detail = f"HSTS Preload: {status}"
                recommendation = ""
                if not passed:
                    recommendation = f"Submit {clean_domain} to https://hstspreload.org/ for automatic HTTPS enforcement in Chrome, Firefox, and Safari."

                return CheckResult(
                    check_id="ext_hsts_preload",
                    check_name="HSTS Preload List",
                    category=self.category_name,
                    severity=Severity.LOW,
                    passed=passed,
                    score=100 if passed else 0,
                    detail=detail,
                    recommendation=recommendation,
                    data={"status": status},
                )
            else:
                return CheckResult(
                    check_id="ext_hsts_preload",
                    check_name="HSTS Preload List",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=True,
                    score=100,
                    detail=f"HSTS Preload API returned HTTP {resp.status_code} — check skipped",
                    recommendation="",
                )

        return self._safe_check(
            "ext_hsts_preload",
            "HSTS Preload List",
            Severity.LOW,
            _run,
        )

    def _check_whois(self, domain: str) -> CheckResult:
        """Check domain registration details via WHOIS (local, no API key)."""
        def _run():
            try:
                import whois
            except ImportError:
                return CheckResult(
                    check_id="ext_whois",
                    check_name="Domain WHOIS (Age, Expiry, Registrar)",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=True,
                    score=100,
                    detail="python-whois package not installed — check skipped. Install with: pip install python-whois",
                    recommendation="",
                    data={"available": False},
                )

            clean_domain = domain.split(":")[0]
            w = whois.whois(clean_domain)

            registrar = w.registrar or "Unknown"
            creation_date = w.creation_date
            expiration_date = w.expiration_date
            name_servers = w.name_servers or []

            # Handle list or single value for dates
            if isinstance(creation_date, list):
                creation_date = creation_date[0] if creation_date else None
            if isinstance(expiration_date, list):
                expiration_date = expiration_date[0] if expiration_date else None

            now = datetime.now(timezone.utc)

            # Calculate domain age in years
            age_years = None
            if creation_date:
                if creation_date.tzinfo is None:
                    creation_date = creation_date.replace(tzinfo=timezone.utc)
                age_days = (now - creation_date).days
                age_years = round(age_days / 365.25, 1)

            # Check if domain is expiring soon
            days_to_expiry = None
            if expiration_date:
                if expiration_date.tzinfo is None:
                    expiration_date = expiration_date.replace(tzinfo=timezone.utc)
                days_to_expiry = (expiration_date - now).days

            # Build detail string
            parts = []
            if age_years is not None:
                parts.append(f"Registered {age_years} years ago")
            if days_to_expiry is not None:
                if days_to_expiry < 0:
                    parts.append(f"EXPIRED {abs(days_to_expiry)} days ago")
                elif days_to_expiry < 30:
                    parts.append(f"⚠️ Expires in {days_to_expiry} days")
                elif days_to_expiry < 90:
                    parts.append(f"Expires in {days_to_expiry} days")
                else:
                    parts.append(f"Expires in {days_to_expiry} days")
            parts.append(f"Registrar: {registrar}")
            if name_servers:
                parts.append(f"NS: {', '.join(name_servers[:3])}")

            detail = " | ".join(parts)

            # Pass if domain exists and isn't expired
            passed = days_to_expiry is None or days_to_expiry > 0

            recommendation = ""
            if days_to_expiry is not None and days_to_expiry < 30 and days_to_expiry >= 0:
                recommendation = f"Your domain expires in {days_to_expiry} days. Renew immediately to avoid losing your domain."
            elif days_to_expiry is not None and days_to_expiry < 0:
                recommendation = f"Your domain expired {abs(days_to_expiry)} days ago! Renew immediately."
            elif age_years is not None and age_years < 1:
                recommendation = "Your domain is less than a year old. New domains may have lower trust signals for search engines."

            return CheckResult(
                check_id="ext_whois",
                check_name="Domain WHOIS (Age, Expiry, Registrar)",
                category=self.category_name,
                severity=Severity.LOW,
                passed=passed,
                score=100 if passed else 0,
                detail=detail,
                recommendation=recommendation,
                data={
                    "registrar": registrar,
                    "age_years": age_years,
                    "days_to_expiry": days_to_expiry,
                    "name_servers": name_servers[:5] if name_servers else [],
                    "available": True,
                },
            )

        return self._safe_check(
            "ext_whois",
            "Domain WHOIS (Age, Expiry, Registrar)",
            Severity.LOW,
            _run,
        )

    def _check_wappalyzer(self, crawl_result) -> CheckResult:
        """Detect tech stack using Wappalyzer Python package (local, no API key)."""
        def _run():
            try:
                from wappalyzer import Wappalyzer, WebPage
            except ImportError:
                return CheckResult(
                    check_id="ext_wappalyzer",
                    check_name="Technology Stack (Wappalyzer)",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=True,
                    score=100,
                    detail="Wappalyzer Python package not installed — check skipped. Install with: pip install wappalyzer",
                    recommendation="",
                    data={"available": False},
                )

            webpage = WebPage.new_from_url(crawl_result.base_url, timeout=15)
            wappalyzer = Wappalyzer.latest()
            technologies = wappalyzer.analyze(webpage)

            if technologies:
                # Categorize detected technologies
                categories = {}
                for tech in technologies:
                    tech_cats = getattr(tech, "categories", [])
                    for cat in tech_cats:
                        cat_name = cat if isinstance(cat, str) else getattr(cat, "name", str(cat))
                        if cat_name not in categories:
                            categories[cat_name] = []
                        categories[cat_name].append(tech.name)

                tech_list = sorted(technologies, key=lambda t: t.name)
                passed = len(tech_list) > 0
                detail = f"Wappalyzer: {len(tech_list)} technologies detected"
                if tech_list:
                    detail += f" — {', '.join(t.name for t in tech_list[:15])}"
                    if len(tech_list) > 15:
                        detail += f" and {len(tech_list) - 15} more"

                return CheckResult(
                    check_id="ext_wappalyzer",
                    check_name="Technology Stack (Wappalyzer)",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=passed,
                    score=100 if passed else 50,
                    detail=detail,
                    recommendation="",
                    data={"technologies": [t.name for t in tech_list], "categories": {k: v for k, v in categories.items()}, "available": True},
                )
            else:
                return CheckResult(
                    check_id="ext_wappalyzer",
                    check_name="Technology Stack (Wappalyzer)",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=True,
                    score=100,
                    detail="Wappalyzer: No technologies detected",
                    recommendation="",
                    data={"technologies": [], "available": True},
                )

        return self._safe_check(
            "ext_wappalyzer",
            "Technology Stack (Wappalyzer)",
            Severity.INFO,
            _run,
        )
