"""External Intelligence checks — free APIs, no API keys required."""
import json
import re
from urllib.parse import urlparse
from curl_cffi import requests as req
from .base import CheckResult, Severity, CheckCategory


class ExternalIntelligenceChecks(CheckCategory):
    category_name = "External Intelligence"
    category_weight = 5  # 5% — supplementary, not core

    def run(self, crawl_result) -> list:
        results = []
        base_url = crawl_result.base_url
        domain = urlparse(base_url).netloc

        results.append(self._check_mozilla_observatory(domain))
        results.append(self._check_crt_sh(domain))
        results.append(self._check_hsts_preload(domain))
        results.append(self._check_whatweb(crawl_result))
        results.append(self._check_wappalyzer(crawl_result))
        return results

    def _check_mozilla_observatory(self, domain: str) -> CheckResult:
        """Check security headers via Mozilla Observatory free API."""
        try:
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
        except Exception as e:
            return CheckResult(
                check_id="ext_mozilla_observatory",
                check_name="Mozilla Observatory (Security Headers)",
                category=self.category_name,
                severity=Severity.INFO,
                passed=True,
                score=100,
                detail=f"Mozilla Observatory API unavailable: {e}",
                recommendation="",
                data={"error": str(e)},
            )

    def _check_crt_sh(self, domain: str) -> CheckResult:
        """Check SSL certificate history via crt.sh free API."""
        try:
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
        except Exception as e:
            return CheckResult(
                check_id="ext_crt_sh",
                check_name="SSL Certificate History (crt.sh)",
                category=self.category_name,
                severity=Severity.INFO,
                passed=True,
                score=100,
                detail=f"crt.sh API unavailable: {e}",
                recommendation="",
                data={"error": str(e)},
            )

    def _check_hsts_preload(self, domain: str) -> CheckResult:
        """Check if domain is in Chrome's HSTS preload list."""
        try:
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
        except Exception as e:
            return CheckResult(
                check_id="ext_hsts_preload",
                check_name="HSTS Preload List",
                category=self.category_name,
                severity=Severity.INFO,
                passed=True,
                score=100,
                detail=f"HSTS Preload API unavailable: {e}",
                recommendation="",
                data={"error": str(e)},
            )

    def _check_whatweb(self, crawl_result) -> CheckResult:
        """Detect tech stack using WhatWeb CLI if available."""
        import subprocess
        import shutil

        whatweb_path = shutil.which("whatweb")
        if not whatweb_path:
            return CheckResult(
                check_id="ext_whatweb",
                check_name="Technology Stack (WhatWeb)",
                category=self.category_name,
                severity=Severity.INFO,
                passed=True,
                score=100,
                detail="WhatWeb CLI not installed — check skipped. Install with: apt install whatweb",
                recommendation="",
                data={"available": False},
            )

        try:
            result = subprocess.run(
                [whatweb_path, "--no-errors", "--quiet", crawl_result.base_url],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout.strip()
            if output:
                # Parse WhatWeb output — format: "URL [tech1, tech2, ...]"
                techs = []
                if "[" in output and "]" in output:
                    tech_part = output[output.index("[") + 1 : output.index("]")]
                    techs = [t.strip() for t in tech_part.split(",") if t.strip()]

                passed = len(techs) > 0
                detail = f"WhatWeb: {len(techs)} technologies detected"
                if techs:
                    detail += f" — {', '.join(techs[:10])}"
                    if len(techs) > 10:
                        detail += f" and {len(techs) - 10} more"

                return CheckResult(
                    check_id="ext_whatweb",
                    check_name="Technology Stack (WhatWeb)",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=passed,
                    score=100 if passed else 50,
                    detail=detail,
                    recommendation="",
                    data={"technologies": techs, "available": True},
                )
            else:
                return CheckResult(
                    check_id="ext_whatweb",
                    check_name="Technology Stack (WhatWeb)",
                    category=self.category_name,
                    severity=Severity.INFO,
                    passed=True,
                    score=100,
                    detail="WhatWeb: No output returned",
                    recommendation="",
                    data={"available": True},
                )
        except subprocess.TimeoutExpired:
            return CheckResult(
                check_id="ext_whatweb",
                check_name="Technology Stack (WhatWeb)",
                category=self.category_name,
                severity=Severity.INFO,
                passed=True,
                score=100,
                detail="WhatWeb timed out — check skipped",
                recommendation="",
                data={"available": True, "error": "timeout"},
            )
        except Exception as e:
            return CheckResult(
                check_id="ext_whatweb",
                check_name="Technology Stack (WhatWeb)",
                category=self.category_name,
                severity=Severity.INFO,
                passed=True,
                score=100,
                detail=f"WhatWeb error: {e}",
                recommendation="",
                data={"available": True, "error": str(e)},
            )

    def _check_wappalyzer(self, crawl_result) -> CheckResult:
        """Detect tech stack using Wappalyzer Python package (local, no API key)."""
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

        try:
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
        except Exception as e:
            return CheckResult(
                check_id="ext_wappalyzer",
                check_name="Technology Stack (Wappalyzer)",
                category=self.category_name,
                severity=Severity.INFO,
                passed=True,
                score=100,
                detail=f"Wappalyzer error: {e}",
                recommendation="",
                data={"available": True, "error": str(e)},
            )
