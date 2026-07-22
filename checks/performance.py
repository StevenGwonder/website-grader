from .base import CheckResult, Severity, CheckCategory
from typing import List
import re

class PerformanceChecks(CheckCategory):
    category_name = "Performance"
    category_weight = 15

    def run(self, crawl_result) -> List[CheckResult]:
        results = []
        page = crawl_result.homepage
        if not page:
            return results

        results.append(self._check_ttfb(page))
        results.append(self._check_page_weight(page))
        results.append(self._check_compression(page))
        results.append(self._check_cache_headers(page))
        results.append(self._check_images(page))
        results.append(self._check_css_js(page))
        results.append(self._check_minification(page))
        results.append(self._check_server_header(page))
        return results

    def _check_ttfb(self, page) -> CheckResult:
        ttfb = page.ttfb_ms
        if ttfb < 200:
            score = 100
        elif ttfb < 500:
            score = 80
        elif ttfb < 1000:
            score = 60
        else:
            score = 30
        passed = ttfb < 1000
        return CheckResult(
            check_id="performance_ttfb",
            check_name="Time to First Byte",
            category=self.category_name,
            severity=Severity.CRITICAL,
            passed=passed,
            score=score,
            detail=f"TTFB: {ttfb:.0f}ms",
            recommendation="Reduce server response time to improve TTFB. Use a CDN (Cloudflare, Fastly), enable server-side caching (Redis/Varnish), and upgrade to a faster hosting plan if TTFB exceeds 600ms.",
            fix_difficulty="Medium (server config)",
        )

    def _check_page_weight(self, page) -> CheckResult:
        size_bytes = len(page.html)
        size_kb = size_bytes / 1024
        size_mb = size_bytes / (1024 * 1024)
        if size_bytes < 500 * 1024:
            score = 100
        elif size_bytes < 1.5 * 1024 * 1024:
            score = 70
        else:
            score = 30
        passed = size_bytes < 1.5 * 1024 * 1024
        return CheckResult(
            check_id="performance_page_weight",
            check_name="Page Weight",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=score,
            detail=f"Page weight: {size_kb:.1f}KB ({size_mb:.2f}MB)",
            recommendation="Optimize images (convert to WebP, compress with TinyPNG), minify CSS/JS (use terser/cssnano), and remove unused JavaScript and CSS to reduce page weight below 1.5MB.",
        )

    def _check_compression(self, page) -> CheckResult:
        encoding = page.headers.get('content-encoding', '').lower()
        passed = encoding in ('gzip', 'br')
        score = 100 if passed else 0
        fix_code = (
            "<IfModule mod_deflate.c>\n"
            "  AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript\n"
            "</IfModule>"
        )
        return CheckResult(
            check_id="performance_compression",
            check_name="Compression",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=score,
            detail=f"Compression: {encoding or 'none'}",
            recommendation="Enable GZIP or Brotli compression on your server.",
            fix_code=fix_code,
        )

    def _check_cache_headers(self, page) -> CheckResult:
        headers = page.headers
        has_cache_control = 'cache-control' in headers
        has_etag = 'etag' in headers
        present = []
        if has_cache_control:
            present.append('cache-control')
        if has_etag:
            present.append('etag')
        score = int((has_cache_control + has_etag) / 2 * 100)
        passed = has_cache_control and has_etag
        fix_code = (
            "<IfModule mod_expires.c>\n"
            "  ExpiresActive On\n"
            "  ExpiresByType image/jpg \"access 1 year\"\n"
            "  ExpiresByType image/jpeg \"access 1 year\"\n"
            "  ExpiresByType image/gif \"access 1 year\"\n"
            "  ExpiresByType image/png \"access 1 year\"\n"
            "  ExpiresByType text/css \"access 1 month\"\n"
            "  ExpiresByType text/html \"access 1 month\"\n"
            "  ExpiresByType application/pdf \"access 1 month\"\n"
            "  ExpiresByType text/x-javascript \"access 1 month\"\n"
            "  ExpiresByType application/x-shockwave-flash \"access 1 month\"\n"
            "  ExpiresByType image/x-icon \"access 1 year\"\n"
            "  ExpiresDefault \"access 1 month\"\n"
            "</IfModule>\n"
            "<IfModule mod_headers.c>\n"
            "  Header unset ETag\n"
            "  FileETag None\n"
            "</IfModule>"
        )
        return CheckResult(
            check_id="performance_cache_headers",
            check_name="Cache Headers",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=score,
            detail=f"Cache headers present: {', '.join(present) if present else 'none'}",
            recommendation="Add cache-control headers and ETags to improve repeat visits.",
            fix_code=fix_code,
        )

    def _check_images(self, page) -> CheckResult:
        imgs = page.soup.find_all('img')
        total = len(imgs)
        if total == 0:
            return CheckResult(
                check_id="performance_images",
                check_name="Image Optimization",
                category=self.category_name,
                severity=Severity.HIGH,
                passed=True,
                score=100,
                detail="No images found",
                recommendation="",
            )

        lazy_count = sum(1 for img in imgs if img.get('loading') == 'lazy')
        format_scores = []
        modern_count = 0
        legacy_count = 0
        for img in imgs:
            src = img.get('src', '') or img.get('data-src', '')
            if not src:
                format_scores.append(0)
                continue
            ext = src.split('.')[-1].lower().split('?')[0]
            if ext == 'webp':
                format_scores.append(100)
                modern_count += 1
            elif ext in ('jpg', 'jpeg', 'png'):
                format_scores.append(70)
                legacy_count += 1
            elif ext in ('avif', 'svg'):
                format_scores.append(100)
                modern_count += 1
            else:
                format_scores.append(30)

        avg_format = sum(format_scores) / total
        lazy_score = (lazy_count / total) * 100
        score = int((avg_format + lazy_score) / 2)
        passed = score > 70

        modern_str = f"{modern_count} in modern formats" if modern_count > 0 else "0 in modern formats"
        legacy_str = f"{legacy_count} in legacy formats (jpg/png)" if legacy_count > 0 else ""
        detail = f"Found {total} images, {lazy_count} with lazy loading, {modern_str}"
        if legacy_str:
            detail += f", {legacy_str}"

        # Smart recommendation based on actual state
        if legacy_count > 0 and modern_count == 0:
            recommendation = "Convert images to WebP/AVIF format and add lazy loading."
        elif legacy_count > 0 and modern_count > 0:
            recommendation = f"Convert remaining {legacy_count} legacy image(s) to WebP/AVIF format."
        elif lazy_count < total:
            recommendation = f"Add loading='lazy' to {total - lazy_count} image(s) without it."
        else:
            recommendation = ""  # Everything looks good

        return CheckResult(
            check_id="performance_images",
            check_name="Image Optimization",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=score,
            detail=detail,
            recommendation=recommendation,
        )

    def _check_css_js(self, page) -> CheckResult:
        css_count = len(page.soup.find_all('link', rel='stylesheet'))
        js_tags = page.soup.find_all('script', src=True)
        js_count = len(js_tags)
        deferred = sum(1 for js in js_tags if js.get('defer') or js.get('async'))
        total = css_count + js_count
        if total < 10:
            score = 100
        elif total < 20:
            score = 70
        else:
            score = 30
        passed = total < 20
        detail = f"CSS: {css_count} files, JS: {js_count} files ({deferred} deferred/async)"
        return CheckResult(
            check_id="performance_css_js",
            check_name="CSS/JS Resources",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=score,
            detail=detail,
            recommendation="Reduce number of CSS/JS files and use async/defer for scripts.",
        )

    def _check_minification(self, page) -> CheckResult:
        html = page.html
        stripped = re.sub(r'>\s+<', '><', html)
        stripped = re.sub(r'\s+', ' ', stripped)
        stripped = stripped.strip()
        ratio = len(html) / len(stripped) if stripped else 1
        passed = ratio < 1.3
        score = 100 if passed else 30
        est_size = int(len(stripped))
        detail = f"HTML size: {len(html)} bytes, minifiable to ~{est_size} bytes"
        return CheckResult(
            check_id="performance_minification",
            check_name="HTML Minification",
            category=self.category_name,
            severity=Severity.LOW,
            passed=passed,
            score=score,
            detail=detail,
            recommendation="Minify HTML to reduce file size.",
        )

    def _check_server_header(self, page) -> CheckResult:
        server = page.headers.get('server', '').strip() or 'not disclosed'
        detail = f"Server: {server}"
        return CheckResult(
            check_id="performance_server_header",
            check_name="Server Header",
            category=self.category_name,
            severity=Severity.LOW,
            passed=True,
            score=100,
            detail=detail,
            recommendation="",
        )
