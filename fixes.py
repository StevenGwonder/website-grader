from checks.base import CheckResult

def generate_fixes(crawl_result, results) -> dict:
    check_fixes = {
        r.check_id: r.fix_code
        for r in results
        if r.fix_code is not None
    }
    return {
        "check_fixes": check_fixes,
        "templates": {
            "robots_txt": gen_robots_txt(crawl_result.base_domain),
            "sitemap_xml": gen_sitemap_xml(list(crawl_result.pages.keys())),
            "htaccess_security": gen_htaccess_security()
        }
    }

def gen_robots_txt(domain) -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: https://{domain}/sitemap.xml"

def gen_sitemap_xml(urls) -> str:
    urls_str = "\n".join(f"  <url><loc>{url}</loc></url>" for url in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls_str}\n</urlset>'

def gen_htaccess_security() -> str:
    return """<IfModule mod_headers.c>
  Header set X-Frame-Options "SAMEORIGIN"
  Header set X-Content-Type-Options "nosniff"
  Header set Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
  Header set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>"""
