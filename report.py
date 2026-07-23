#!/usr/bin/env python3
"""
HTML report generator — self-contained, NWP branded, printable.
Implements a next-generation dark dashboard with orange/blue brand colors,
explicit "Where" & "Why" structured outputs, and a programmatic sales summary.
"""
import json
from checks.base import Severity

# NWP brand colors
BG = "#0b0f19"         # Deep space dark blue-black
CARD = "#111827"       # Dark grey-blue card background
BORDER = "#1f2937"     # Muted border
ORANGE = "#f97316"     # Accent orange
BLUE = "#38bdf8"       # Accent blue
TEXT = "#f3f4f6"       # Light grey text
MUTED = "#9ca3af"      # Muted grey text

SEVERITY_COLORS = {
    Severity.CRITICAL: "#ef4444", # Rose red
    Severity.HIGH: "#f59e0b",     # Amber
    Severity.MEDIUM: "#38bdf8",   # Sky blue
    Severity.LOW: "#9ca3af",      # Muted grey
    Severity.INFO: "#6b7280",     # Muted light grey
}

# Extensive mapping of check IDs to their professional "Why It Matters" business impact
WHY_MAP = {
    # Technical SEO
    "tech_meta_title": "Search engines display the title tag as the clickable headline in search results. A well-written, keyword-optimized title is the single most important on-page ranking factor and directly determines your click-through rate (CTR) and initial keyword relevance.",
    "tech_meta_desc": "The meta description serves as organic ad copy in search results. A compelling, concise summary with an actionable CTA can increase clicks by up to 30%, driving traffic even if your organic ranking position does not change.",
    "tech_headings": "Proper heading tags (H1-H6) act as a table of contents for crawlers and screen readers. Correct hierarchy allows search engines to understand the core topics of your page and prevents indexing confusion.",
    "tech_canonical": "Canonical tags guide search engines to the preferred version of a page, preventing duplicate content penalties caused by multiple URL variations (such as HTTP/HTTPS, www/non-www, or tracking parameters).",
    "tech_robots_meta": "Robots meta tags control search indexer behavior at the page level. Misconfigured tags can lead to search engine lockout, preventing critical landing pages from ever appearing in search listings.",
    "tech_schema": "Structured data (JSON-LD) translates human-readable content into machine-readable formats. It enables rich snippets (stars, FAQs, event details) in search results, increasing search visibility and user trust.",
    "tech_og_tags": "Open Graph tags format how your website links appear when shared on social platforms like Facebook, LinkedIn, and Slack. Proper tags ensure your brand has professional visual cards that drive social clicks.",
    "tech_twitter_cards": "Twitter Card tags ensure your links render with high-impact visual previews on Twitter/X, maximizing engagement and preventing plain, text-only link shares.",
    "tech_favicon": "Favicons appear in browser tabs, bookmarks, and mobile search listings. They build brand recall, establish digital professionalism, and increase user trust during browsing sessions.",
    "tech_sitemap": "An XML sitemap acts as a roadmap for search indexers, ensuring all page URLs are discovered and indexed, including deep-nested content that crawler bots might otherwise miss.",
    "tech_robots_txt": "The robots.txt file manages crawler search budgets and access routes. Misconfigurations can block critical bots, while correct configuration directs crawlers to index your most valuable pages.",
    "tech_broken_links": "Broken links (404/500 errors) frustrate visitors, drain your crawl budget, and signal to search engines that the website is neglected, leading to lower search rankings.",
    "tech_redirects": "Multiple consecutive redirects add connection latency (TTFB) and dilute link equity (SEO authority). Direct links keep connections fast and pass maximum page authority.",
    "tech_internal_links": "Internal linking distributes search engine authority (PageRank) across your pages and establishes a logical site architecture, helping search engines crawl and rank deeper pages.",
    "tech_url_structure": "Clean, readable URL structures containing keywords improve user experience and allow search crawlers to predict page topics from the URL string alone.",
    "tech_pagination": "Pagination tags (rel=next/prev) clarify relationship flows between paginated lists, preventing search engines from treating list pages as duplicate content.",
    "tech_breadcrumbs": "Breadcrumbs provide a structural navigation trail for users and search engines, showing the user's location in your site hierarchy and enhancing Google mobile search snippet displays.",
    
    # Performance
    "performance_ttfb": "Time to First Byte measures server response latency. A slow TTFB (>600ms) delays the entire page render cycle, driving up user bounce rates and penalizing search engine rankings.",
    "performance_page_weight": "Large page payloads consume mobile data and increase load times on slow cellular networks. Keeping page sizes under 1MB ensures immediate access and high conversion rates.",
    "performance_compression": "Brotli or Gzip compression shrinks text-based assets (HTML, CSS, JS) by up to 70%, dramatically reducing network transfer times and bandwidth consumption.",
    "performance_cache_headers": "Leveraging browser caching stores static assets locally on user devices, eliminating redundant network calls and making repeat visits feel instantaneous.",
    "performance_images": "Unoptimized images are the #1 cause of slow websites. Modern formats like WebP or AVIF reduce image file sizes by up to 80% without losing quality, and lazy loading defers offscreen downloads.",
    "performance_css_js": "Excessive CSS and JS files block rendering and increase main-thread blocking time. Bundling files and using async/defer loading keeps the page interactive during rendering.",
    "performance_minification": "Minifying code removes comments, formatting, and whitespace, reducing source code sizes and speeding up asset downloads for visitors.",
    "performance_server_header": "Disclosing specific backend server versions exposes infrastructure details to automated vulnerability scanners, making your server a target for exploits.",
    
    # Local SEO
    "local_seo_nap_extraction": "Name, Address, and Phone (NAP) details establish localized search authority. Search engines crawl this data to confirm your physical business location for local pack matches.",
    "local_seo_nap_consistency": "Mismatched NAP details across web pages raise trust issues for search algorithms. Identical NAP details confirm listing authenticity, boosting local pack prominence.",
    "local_seo_localbusiness_schema": "LocalBusiness schema structures business listings directly for indexers. It links business names, geo-coordinates, reviews, and hours, driving business visibility in local packs.",
    "local_seo_maps_embed": "A Google Map embed confirms physical location relevance, makes navigation easy for local customers, and increases localized authority.",
    "local_seo_service_area": "Declaring service areas (cities, counties, regions) clarifies business coverage to local searchers, helping match your site with searches in target cities.",
    "local_seo_city_targeting": "Targeting specific city keywords in titles, headings, and descriptions ensures relevance for geo-modified searches (e.g., 'plumber in Dallas').",
    "local_seo_review_schema": "Review structured data (AggregateRating) displays star ratings in search results, increasing click-through rates (CTR) and establishing instant digital trust.",
    "local_seo_gbp_link": "Linking directly to your Google Business Profile page synchronizes on-page local listings with Google Maps data, reinforcing geographic relevance.",
    
    # Content Quality
    "content_word_count": "Thin content (<200 words) fails to provide enough topic depth for search engines to rank the page. Deep content provides answers to customer search intents.",
    "content_keyword_density": "Over-optimization or keyword stuffing leads to search engine penalties. Keeping target keyword density between 1-3% ensures natural reading and search relevance.",
    "content_readability": "Plain, clear reading text improves accessibility, increases time-on-site, and satisfies screen readers and voice searchers.",
    "content_faq": "FAQ sections answer customer queries, keep users on your page longer, and capture high-value organic search real estate like 'People Also Ask' rich snippets.",
    "content_eeat": "E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) is Google's core framework for content evaluation. Author bios, trust badges, and credentials build human and algorithmic trust.",
    "content_uniqueness": "Internal duplicate content confuses search engine indexers regarding which page to rank, diluting organic search performance across your site.",
    "content_title_alignment": "Mismatched titles and page content disappoint visitors and lead to high bounce rates. Direct semantic alignment confirms relevance, satisfying search algorithms.",
    
    # Security
    "ssl": "SSL encryption (HTTPS) is a critical Google ranking factor and secure web baseline. It protects user inputs from interception and prevents browser warnings from scaring away visitors.",
    "security_headers": "Defensive HTTP headers (CSP, HSTS, X-Frame) protect your website against client-side scripting attacks, cross-site scripting (XSS), clickjacking, and mime-sniffing exploits.",
    "mixed_content": "Mixed content occurs when an HTTPS page requests resource files over unencrypted HTTP. Modern browsers block these mixed assets, triggering security warnings.",
    
    # Accessibility
    "accessibility_alt_text": "Alternative text describes graphics to visually impaired users and screen-readers. Alt tags also index images for search engines, capturing image search traffic.",
    "accessibility_form_labels": "Every input field must have an associated text label tag. Labels guide screen readers, assist autofill features, and improve conversion flow.",
    "accessibility_heading_order": "A clean H1->H2->H3 heading sequence provides a logical reading flow, helping assistive readers parse page layout.",
    "accessibility_aria_labels": "ARIA labels clarify interactive button actions that contain only graphics, allowing screen readers and autonomous bots to parse button functions.",
    "accessibility_skip_nav": "A skip navigation link allows keyboard-only users to bypass navigation menus and jump directly to main content, fulfilling key WCAG requirements.",
    
    # Conversion
    "conversion_social_links": "Social media links connect users to your active social pages, building brand authority, and encouraging customer review research.",
    "conversion_analytics": "Tracking tags (GA4, Tag Manager, Facebook Pixel) provide visitor flow data, allowing you to measure conversion rates and optimize ad campaigns.",
    "conversion_cta_elements": "Clear call-to-action buttons (e.g., 'Book a Call', 'Request Quote') guide visitors through conversion flows, transforming passive readers into active sales leads.",
    "conversion_trust_signals": "Trust badges, certifications, professional accreditations, and license numbers address buyer anxiety and increase form conversion rates.",
    "conversion_contact_form": "On-page contact forms lower the effort required to contact you, maximizing lead capture volume compared to simple email links.",

    "alt_text": "Alternative text describes graphics to visually impaired users and screen-readers. Alt tags also index images for search engines, capturing image search traffic.",
    "form_labels": "Every input field must have an associated text label tag. Labels guide screen readers, assist autofill features, and improve conversion flow.",
    "heading_order": "A clean H1->H2->H3 heading sequence provides a logical reading flow, helping assistive readers parse page layout.",
    "aria_labels": "ARIA labels clarify interactive button actions that contain only graphics, allowing screen readers and autonomous bots to parse button functions.",
    "skip_nav": "A skip navigation link allows keyboard-only users to bypass navigation menus and jump directly to main content, fulfilling key WCAG requirements.",

    "social_links": "Social media links connect users to your active social pages, building brand authority, and encouraging customer review research.",
    "analytics": "Tracking tags (GA4, Tag Manager, Facebook Pixel) provide visitor flow data, allowing you to measure conversion rates and optimize ad campaigns.",
    "cta_elements": "Clear call-to-action buttons (e.g., 'Book a Call', 'Request Quote') guide visitors through conversion flows, transforming passive readers into active sales leads.",
    "trust_signals": "Trust badges, certifications, professional accreditations, and license numbers address buyer anxiety and increase form conversion rates.",
    "contact_form": "On-page contact forms lower the effort required to contact you, maximizing lead capture volume compared to simple email links.",

    "ext_mozilla_observatory": "Mozilla Observatory independently scans your site's security headers and provides a third-party security rating, validating your server-side defense posture.",
    "ext_crt_sh": "Certificate Transparency logs (crt.sh) provide an independent record of all SSL certificates issued for your domain, helping detect unauthorized certificate issuance.",
    "ext_hsts_preload": "HSTS Preload submission ensures browsers always connect to your site over HTTPS, preventing downgrade attacks and SSL stripping on first visit.",
    "ext_whois": "WHOIS data reveals domain registration age, registrar, and expiry date. Older domains with clean registration history tend to rank higher in search results.",
    "ext_wappalyzer": "Technology stack detection identifies the frameworks, CMS, and analytics tools your site uses, helping assess technical debt and upgrade paths.",
}

def _score_color(score):
    if score >= 80: return "#10b981" # Emerald Green
    if score >= 60: return "#f59e0b" # Amber
    if score >= 40: return ORANGE
    return "#ef4444"                 # Rose Red

def _grade_color(grade):
    return {
        "A": "#10b981", 
        "B": "#84cc16", 
        "C": "#f59e0b", 
        "D": ORANGE, 
        "F": "#ef4444"
    }.get(grade, "#ef4444")

def _default_why_text(category):
    """Return meaningful fallback 'Why It Matters' text per category."""
    texts = {
        "Technical SEO": "Technical SEO ensures search engines can properly crawl, index, and render your pages. Issues here directly impact your organic search visibility and can prevent entire sections of your site from appearing in search results.",
        "Performance": "Page speed and performance directly affect user experience, conversion rates, and search engine rankings. Slow-loading pages increase bounce rates and reduce the time users spend on your site.",
        "Content": "Content quality and structure determine how well your pages communicate value to both users and search engines. Well-optimized content drives organic traffic and establishes topical authority.",
        "Local SEO": "Local SEO signals help your business appear in geographically-targeted searches and Google's Local Pack. Consistent NAP (Name, Address, Phone) data across the web builds trust with both users and search algorithms.",
        "Security": "Security measures protect your users' data and your site's integrity. HTTPS, security headers, and proper configurations prevent data breaches and build user trust.",
        "Accessibility": "Web accessibility ensures your site is usable by people with disabilities, expands your audience reach, and is increasingly factored into search engine rankings. It also reduces legal compliance risk.",
        "Social & Conversion": "Social signals and conversion elements turn passive visitors into engaged users and customers. Clear calls-to-action, social proof, and analytics tracking are essential for measuring and improving business outcomes.",
        "External Intelligence": "External data sources provide independent verification of your site's security posture, certificate health, and technology stack. These signals help identify issues that internal checks alone may miss.",
    }
    return texts.get(category, f"Addressing issues in the {category} domain improves overall site quality, user trust, and search engine performance.")

def _bar(label, score, weight):
    color = _score_color(score)
    return f"""
    <div class="bar-row">
      <span class="bar-label">{label} <small>({weight}%)</small></span>
      <div class="bar-track">
        <div class="bar-fill" style="width:{score}%;background:{color};"></div>
      </div>
      <span class="bar-score">{score}</span>
    </div>"""

def _check_row(r):
    icon = "✓" if r.passed else "✗"
    status_class = "passed" if r.passed else "failed"
    color = SEVERITY_COLORS.get(r.severity, "#9ca3af")
    
    # Extract location (where) & impact (why)
    where_text = r.detail
    why_text = WHY_MAP.get(r.check_id, _default_why_text(r.category))
    
    fix_section = ""
    if not r.passed:
        # Add "Learn more" links from registry documentation_references
        from checks.registry import get_rule_metadata
        meta = get_rule_metadata(r.check_id)
        learn_more_links = ""
        if meta and meta.documentation_references:
            learn_more_links = '<div class="check-section" style="margin-top:8px;">' + \
                '<span class="section-title" style="color:var(--blue);">📖 Learn More</span>' + \
                ''.join(f'<a href="{ref}" target="_blank" style="display:inline-block;margin-right:12px;font-size:0.85em;color:var(--blue);text-decoration:underline;">{ref.split("//")[-1].split("/")[0] if "//" in ref else ref}</a>' for ref in meta.documentation_references) + \
                '</div>'
        fix_section = f"""
        <div class="check-section check-how">
          <span class="section-title">🛠️ How to Fix (Recommendation)</span>
          <span class="section-val">{r.recommendation or 'Implement programmatic corrections in accordance with standard web layouts.'}</span>
        </div>
        {learn_more_links}
        """
        
    code_section = ""
    if r.fix_code and not r.passed:
        code_section = f"""
        <div class="fix-code-block">
          <div class="code-header">
            <span>🔧 Suggested Code Correction</span>
            <button class="copy-btn" onclick="copyCode(this)">Copy Code</button>
          </div>
          <pre><code>{r.fix_code}</code></pre>
        </div>
        """

    # If it is failed, we start it expanded by default. Otherwise collapsed.
    expanded_class = "expanded" if not r.passed else ""

    return f"""
    <div class="check-card {status_class} {expanded_class}" data-category="{r.category}" data-passed="{str(r.passed).lower()}" data-severity="{r.severity.value}">
      <div class="check-header" onclick="toggleCard(this)">
        <span class="check-status-badge {status_class}">{icon}</span>
        <span class="check-name">{r.check_name}</span>
        <div class="check-badges">
          <span class="badge category-badge">{r.category}</span>
          <span class="badge severity-badge" style="background:{color}15; color:{color}; border: 1px solid {color}30;">{r.severity.value.upper()}</span>
        </div>
        <span class="accordion-arrow">▼</span>
      </div>
      <div class="check-body">
        <div class="check-grid">
          <div class="check-section check-where">
            <span class="section-title">🔍 Where (Location / Value Found)</span>
            <span class="section-val">{where_text}</span>
          </div>
          <div class="check-section check-why">
            <span class="section-title">💡 Why (Business & AI Impact)</span>
            <span class="section-val">{why_text}</span>
          </div>
        </div>
        {fix_section}
        {code_section}
      </div>
    </div>"""

def _nap_table(crawl_result, all_results):
    nap_result = next((r for r in all_results if r.check_id == "local_seo_nap_consistency"), None)
    if not nap_result or not nap_result.data.get("nap_per_page"):
        return ""
    rows = ""
    for url, nap in nap_result.data["nap_per_page"].items():
        short_url = url.replace("https://", "").replace("http://", "")[:40]
        rows += f"""
        <tr>
          <td><strong>{short_url}</strong></td>
          <td>{nap.get('name') or '—'}</td>
          <td>{nap.get('phone') or '—'}</td>
          <td>{nap.get('address') or '—'}</td>
        </tr>"""
    return f"""
    <div class="table-container">
      <table class="nap-table">
        <thead>
          <tr>
            <th>Page Link</th>
            <th>Name (Schema/Title)</th>
            <th>Phone Extracted</th>
            <th>Address Extracted</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>"""

def _perf_table(crawl_result):
    hp = crawl_result.homepage
    if not hp:
        return ""
    size_kb = len(hp.html) / 1024
    encoding = hp.headers.get("content-encoding", "none")
    cache = "yes" if hp.headers.get("cache-control") else "no"
    return f"""
    <div class="table-container">
      <table class="perf-table">
        <thead>
          <tr>
            <th>Metric Dimension</th>
            <th>Calculated Value</th>
            <th>Standard Reference</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Time to First Byte (TTFB)</strong></td>
            <td class="perf-metric">{hp.ttfb_ms:.0f}ms</td>
            <td>&lt; 200ms (Excellent) | &lt; 600ms (Good)</td>
          </tr>
          <tr>
            <td><strong>Page Payload Weight</strong></td>
            <td class="perf-metric">{size_kb:.1f} KB</td>
            <td>&lt; 500 KB (Optimal) | &lt; 1.5 MB (Acceptable)</td>
          </tr>
          <tr>
            <td><strong>Server Data Compression</strong></td>
            <td class="perf-metric">{encoding}</td>
            <td>Gzip or Brotli (Required)</td>
          </tr>
          <tr>
            <td><strong>Cache Control Policy</strong></td>
            <td class="perf-metric">{cache.upper()}</td>
            <td>Cache headers configured (Required)</td>
          </tr>
        </tbody>
      </table>
    </div>"""

def _action_plan(all_results):
    sev_weight = {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1, Severity.INFO: 0.5}
    failed = [r for r in all_results if not r.passed]
    failed.sort(key=lambda r: sev_weight.get(r.severity, 0), reverse=True)
    top = failed[:10]
    if not top:
        return '<div class="passed-alert">🎉 **Congratulations!** No critical or failed issues were detected on this site.</div>'
    items = ""
    for i, r in enumerate(top, 1):
        color = SEVERITY_COLORS.get(r.severity, "#9ca3af")
        items += f"""
        <div class="action-item">
          <div class="action-num-badge">{i}</div>
          <div class="action-content">
            <div class="action-meta">
              <span class="action-title">{r.check_name}</span>
              <span class="action-badge" style="background:{color}15; color:{color}; border: 1px solid {color}30;">{r.severity.value.upper()}</span>
            </div>
            <div class="action-desc">
              <strong>Problem:</strong> {r.detail}<br>
              <strong>Resolution:</strong> {r.recommendation}
            </div>
          </div>
        </div>"""
    return f"""<div class="action-plan-list">{items}</div>"""

def _sales_summary(score_data, all_results):
    """Generate a programmatic sales summary paragraph based on category sub-scores."""
    cats = [(cat, d["score"]) for cat, d in score_data["categories"].items()]
    cats.sort(key=lambda x: x[1])  # ascending by score
    weakest = cats[:2] if len(cats) >= 2 else cats + [("N/A", 0)]

    score = score_data["overall_score"]
    w1_name, w1_score = weakest[0]
    w2_name, w2_score = weakest[1] if len(weakest) > 1 else ("N/A", 0)

    if score < 40:
        text = (
            f"Your website is struggling to perform. Your biggest issues are in "
            f"{w1_name} (scoring just {w1_score}%) and {w2_name}. "
            f"These problems are likely costing you customers every day. I can help you fix these quickly."
        )
    elif score < 70:
        text = (
            f"Your website has a solid foundation, but there's room to grow. "
            f"{w1_name} ({w1_score}%) and {w2_name} are holding back your overall score. "
            f"Addressing these would give you a significant boost."
        )
    elif score < 90:
        text = (
            f"Your website is performing well! A few targeted improvements in "
            f"{w1_name} and {w2_name} could push you into the top tier."
        )
    else:
        text = (
            f"Excellent work — your website is in great shape. "
            f"I'd recommend regular monitoring to keep it that way."
        )

    return f'<div class="card"><h2>📊 Summary</h2><p style="font-size:1.05em;line-height:1.7;color:var(--muted);">{text}</p></div>'


def generate_report(crawl_result, all_results, score_data, fixes, url):
    grade = score_data["grade"]
    score = score_data["overall_score"]
    gcolor = _grade_color(grade)
    scolor = _score_color(score)
    cat_bars = "".join(_bar(cat, d["score"], d["weight"]) for cat, d in score_data["categories"].items())
    checks_html = "".join(_check_row(r) for r in all_results)
    nap = _nap_table(crawl_result, all_results)
    perf = _perf_table(crawl_result)
    plan = _action_plan(all_results)
    sales_summary = _sales_summary(score_data, all_results)
    failed_count = sum(1 for r in all_results if not r.passed)
    passed_count = len(all_results) - failed_count
    total_count = len(all_results)
    high_failed_count = sum(1 for r in all_results if not r.passed and r.severity in (Severity.CRITICAL, Severity.HIGH))
    
    date = crawl_result.homepage.headers.get("date", "") if crawl_result.homepage else ""
    if not date:
        import datetime
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # SVG circular gauge stroke-dashoffset calculations
    # Circumference = 264. Dashoffset = 264 * (1 - score / 100)
    stroke_offset = 264 * (1 - score / 100.0)

    # Load templates from fixes
    robots_tmpl = fixes.get("templates", {}).get("robots_txt", "")
    sitemap_tmpl = fixes.get("templates", {}).get("sitemap_xml", "")
    htaccess_tmpl = fixes.get("templates", {}).get("htaccess_security", "")

    # HTML content as a standard string to avoid python f-string escaping errors with CSS/JS brackets
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Website Audit Dashboard: {URL} — Score {SCORE}/100</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: {BG};
      --card: {CARD};
      --border: {BORDER};
      --orange: {ORANGE};
      --blue: {BLUE};
      --text: {TEXT};
      --muted: {MUTED};
      --passed: #10b981;
      --failed: #ef4444;
      --gold: #f59e0b;
      --card-gradient: linear-gradient(145deg, #1f2937 0%, #111827 100%);
      --orange-glow: rgba(249, 115, 22, 0.15);
      --blue-glow: rgba(56, 189, 248, 0.15);
    }

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding-bottom: 60px;
    }

    .container {
      max-width: 1000px;
      margin: 0 auto;
      padding: 40px 20px;
    }

    /* Header & Branding */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 32px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 24px;
    }

    .brand-group {
      display: flex;
      flex-direction: column;
    }

    .brand-logo {
      font-family: 'Outfit', sans-serif;
      font-size: 1.8em;
      font-weight: 800;
      background: linear-gradient(135deg, var(--orange) 0%, var(--blue) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 4px;
    }

    .audit-meta {
      font-size: 0.9em;
      color: var(--muted);
    }

    .audit-target {
      font-weight: 600;
      color: var(--blue);
      text-decoration: none;
    }

    /* Executive Hero Grid */
    .hero-grid {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 24px;
      margin-bottom: 32px;
    }

    .score-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 32px 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      position: relative;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }

    /* Circular SVG Gauge */
    .radial-gauge-container {
      position: relative;
      width: 140px;
      height: 140px;
      margin-bottom: 16px;
    }

    .score-radial {
      width: 100%;
      height: 100%;
      transform: rotate(-90deg);
    }

    .score-radial-progress {
      color: {SCOLOR};
      transition: stroke-dashoffset 1s ease-in-out;
    }

    .radial-text-container {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
    }

    .radial-score {
      font-family: 'Outfit', sans-serif;
      font-size: 2.2em;
      font-weight: 800;
      color: var(--text);
      line-height: 1;
    }

    .radial-max {
      font-size: 0.8em;
      color: var(--muted);
    }

    .grade-badge {
      font-family: 'Outfit', sans-serif;
      font-size: 1.4em;
      font-weight: 800;
      color: {GCOLOR};
      border: 2px solid {GCOLOR};
      padding: 4px 16px;
      border-radius: 99px;
      margin-bottom: 16px;
      background: {GCOLOR}08;
      box-shadow: 0 0 15px {GCOLOR}20;
    }

    .quick-stats {
      font-size: 0.85em;
      color: var(--muted);
      border-top: 1px solid var(--border);
      width: 100%;
      padding-top: 16px;
      display: flex;
      justify-content: space-around;
    }

    .quick-stats span strong {
      color: var(--text);
    }

    /* Category Breakdown Card */
    .breakdown-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 28px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }

    .breakdown-card h3 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.3em;
      font-weight: 700;
      color: var(--blue);
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .bar-row {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
    }

    .bar-label {
      width: 160px;
      font-size: 0.85em;
      font-weight: 600;
      text-align: right;
      color: var(--text);
      white-space: nowrap;
    }

    .bar-label small {
      color: var(--muted);
      font-weight: 400;
    }

    .bar-track {
      flex: 1;
      background: var(--border);
      border-radius: 99px;
      height: 16px;
      overflow: hidden;
      position: relative;
    }

    .bar-fill {
      height: 100%;
      border-radius: 99px;
      transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .bar-score {
      width: 32px;
      font-size: 0.9em;
      font-weight: 700;
      text-align: left;
    }

    /* Action Plan Dashboard */
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 28px;
      margin-bottom: 32px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }

    .card h2 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.4em;
      font-weight: 700;
      color: var(--orange);
      margin-bottom: 18px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
    }

    .action-plan-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .action-item {
      display: flex;
      gap: 16px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border);
      border-radius: 12px;
      transition: border-color 0.2s;
    }

    .action-item:hover {
      border-color: rgba(249, 115, 22, 0.4);
    }

    .action-num-badge {
      background: var(--orange-glow);
      color: var(--orange);
      font-family: 'Outfit', sans-serif;
      font-size: 1.2em;
      font-weight: 800;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(249, 115, 22, 0.3);
      flex-shrink: 0;
    }

    .action-content {
      flex: 1;
    }

    .action-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .action-title {
      font-weight: 700;
      color: var(--text);
    }

    .action-badge {
      font-size: 0.7em;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .action-desc {
      font-size: 0.85em;
      color: var(--muted);
      line-height: 1.5;
    }

    .action-desc strong {
      color: var(--text);
    }

    /* Tabs & Filters bar */
    .controls-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      gap: 16px;
      flex-wrap: wrap;
    }

    .filter-tabs {
      display: flex;
      background: rgba(255,255,255,0.03);
      padding: 4px;
      border: 1px solid var(--border);
      border-radius: 10px;
      gap: 4px;
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--muted);
      padding: 8px 16px;
      border-radius: 8px;
      font-family: inherit;
      font-size: 0.85em;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .tab-btn:hover {
      color: var(--text);
    }

    .tab-btn.active {
      background: var(--blue);
      color: var(--bg);
      box-shadow: 0 4px 10px rgba(56, 189, 248, 0.3);
    }

    .search-container {
      position: relative;
      flex: 1;
      max-width: 320px;
    }

    .search-input {
      width: 100%;
      background: var(--card);
      border: 1px solid var(--border);
      padding: 10px 16px;
      padding-left: 36px;
      border-radius: 10px;
      color: var(--text);
      font-family: inherit;
      font-size: 0.85em;
    }

    .search-input:focus {
      outline: none;
      border-color: var(--blue);
      box-shadow: 0 0 10px var(--blue-glow);
    }

    .search-icon {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
      font-size: 0.9em;
      pointer-events: none;
    }

    /* Check Cards Grid/List */
    .checks-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .check-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      transition: all 0.2s;
    }

    .check-card:hover {
      border-color: rgba(255, 255, 255, 0.1);
    }

    .check-header {
      padding: 16px 20px;
      display: flex;
      align-items: center;
      cursor: pointer;
      gap: 14px;
      user-select: none;
    }

    .check-status-badge {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8em;
      font-weight: bold;
      flex-shrink: 0;
    }

    .check-status-badge.passed {
      background: rgba(16, 185, 129, 0.1);
      color: var(--passed);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .check-status-badge.failed {
      background: rgba(239, 68, 68, 0.1);
      color: var(--failed);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .check-name {
      font-weight: 600;
      color: var(--text);
      font-size: 0.95em;
    }

    .check-badges {
      margin-left: auto;
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .badge {
      font-size: 0.7em;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      white-space: nowrap;
    }

    .category-badge {
      background: rgba(255,255,255,0.05);
      color: var(--muted);
      border: 1px solid var(--border);
    }

    .accordion-arrow {
      color: var(--muted);
      font-size: 0.8em;
      transition: transform 0.2s;
      margin-left: 8px;
    }

    /* Accordion Body */
    .check-body {
      display: none;
      padding: 20px;
      border-top: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.15);
    }

    .check-card.expanded .check-body {
      display: block;
    }

    .check-card.expanded .accordion-arrow {
      transform: rotate(180deg);
    }

    /* Grid for Where and Why */
    .check-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 16px;
    }

    .check-section {
      background: rgba(255, 255, 255, 0.01);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }

    .section-title {
      display: block;
      font-size: 0.75em;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }

    .check-where .section-title {
      color: var(--blue);
    }

    .check-why .section-title {
      color: var(--gold);
    }

    .check-how .section-title {
      color: var(--orange);
    }

    .section-val {
      font-size: 0.85em;
      color: var(--muted);
      line-height: 1.5;
    }

    .check-how {
      margin-bottom: 16px;
    }

    /* Code Block Fix styling */
    .fix-code-block {
      background: #07090e;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      margin-top: 12px;
    }

    .code-header {
      background: rgba(255, 255, 255, 0.03);
      padding: 8px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      font-size: 0.75em;
      font-weight: 600;
      color: var(--muted);
    }

    .copy-btn {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--muted);
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.2s;
    }

    .copy-btn:hover {
      color: var(--text);
      border-color: var(--muted);
    }

    .fix-code-block pre {
      padding: 16px;
      overflow-x: auto;
    }

    .fix-code-block code {
      font-family: 'Courier New', Courier, monospace;
      font-size: 0.8em;
      color: var(--blue);
      display: block;
      white-space: pre;
    }

    /* Tables general styling */
    .table-container {
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 12px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }

    th, td {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      font-size: 0.85em;
    }

    tr:last-child td {
      border-bottom: none;
    }

    th {
      background: rgba(255,255,255,0.02);
      font-weight: 700;
      color: var(--blue);
      text-transform: uppercase;
      font-size: 0.75em;
      letter-spacing: 0.05em;
    }

    td {
      color: var(--muted);
    }

    td strong {
      color: var(--text);
    }

    .perf-metric {
      font-family: 'Courier New', Courier, monospace;
      font-weight: bold;
      color: var(--orange);
    }

    /* Code Templates Configuration block */
    .config-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      margin-bottom: 32px;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }

    .config-tab-headers {
      display: flex;
      border-bottom: 1px solid var(--border);
      background: rgba(255,255,255,0.02);
    }

    .config-tab-btn {
      background: transparent;
      border: none;
      color: var(--muted);
      padding: 14px 24px;
      font-family: inherit;
      font-size: 0.85em;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      border-bottom: 2px solid transparent;
    }

    .config-tab-btn:hover {
      color: var(--text);
    }

    .config-tab-btn.active {
      color: var(--orange);
      border-bottom-color: var(--orange);
    }

    .config-tab-body {
      padding: 24px;
    }

    .config-pane {
      display: none;
    }

    .config-pane.active {
      display: block;
    }

    .config-desc {
      font-size: 0.85em;
      color: var(--muted);
      margin-bottom: 16px;
    }

    /* Global Footer */
    footer {
      text-align: center;
      margin-top: 48px;
      border-top: 1px solid var(--border);
      padding-top: 24px;
      color: var(--muted);
      font-size: 0.8em;
    }

    /* Responsive grid settings */
    @media (max-width: 768px) {
      .hero-grid {
        grid-template-columns: 1fr;
      }
      .check-grid {
        grid-template-columns: 1fr;
        gap: 12px;
      }
      header {
        flex-direction: column;
        align-items: flex-start;
        gap: 12px;
      }
      .controls-bar {
        flex-direction: column;
        align-items: stretch;
      }
      .search-container {
        max-width: 100%;
      }
    }

    @media print {
      body {
        background-color: #fff;
        color: #000;
      }
      .card, .breakdown-card, .score-card, .check-card {
        border: 1px solid #ccc;
        background: #fff;
        color: #000;
        box-shadow: none;
      }
      .check-body {
        background: #fafafa;
        display: none;
      }
      .check-card.failed .check-body {
        display: block !important;
      }
      .copy-btn, .controls-bar, .copy-btn, .config-tab-headers {
        display: none !important;
      }
      .card:nth-of-type(1) {
        page-break-before: always;
      }
      h2:has(+ .controls-bar) {
        page-break-before: always;
      }
    }
  </style>
</head>
<body>

  <div class="container">
  
    <header>
      <div class="brand-group">
        <span class="brand-logo">North Web Pro Audit</span>
        <span class="audit-meta">Target: <a class="audit-target" href="{URL}" target="_blank">{URL}</a></span>
      </div>
      <div class="audit-meta" style="text-align: right;">
        <div>Programmatic Grader v2.0</div>
        <div>Date: {DATE}</div>
      </div>
    </header>

    <!-- Hero Scoreboard -->
    <div class="hero-grid">
    
      <div class="score-card">
        <div class="grade-badge">GRADE {GRADE}</div>
        <div class="radial-gauge-container">
          <svg viewBox="0 0 100 100" class="score-radial">
            <circle cx="50" cy="50" r="42" stroke="var(--border)" stroke-width="8" fill="transparent"></circle>
            <circle cx="50" cy="50" r="42" stroke="currentColor" stroke-width="8" fill="transparent" 
                    stroke-dasharray="264" stroke-dashoffset="{STROKE_OFFSET}" 
                    stroke-linecap="round" class="score-radial-progress"></circle>
          </svg>
          <div class="radial-text-container">
            <span class="radial-score">{SCORE}</span>
            <span class="radial-max">/100</span>
          </div>
        </div>
        <div class="quick-stats">
          <span>Passed: <strong>{PASSED_COUNT}</strong></span>
          <span>Failed: <strong>{FAILED_COUNT}</strong></span>
        </div>
        <div class="quick-stats" style="border-top: none; padding-top: 4px; font-size: 0.75em;">
          <span>Coverage: <strong>{COVERAGE_SCORE}%</strong></span>
          <span>Confidence: <strong>{CONFIDENCE_SCORE}%</strong></span>
        </div>
      </div>
      
      <div class="breakdown-card">
        <h3>
          <span>Domain Scores</span>
          <span style="font-size: 0.7em; color: var(--muted); font-weight: normal;">Weighted Average Model</span>
        </h3>
        {CAT_BARS}
      </div>
      
    </div>

    <!-- Sales Summary -->
    {SALES_SUMMARY}

    <!-- Action Plan Card -->
    <div class="card">
      <h2>📋 Prioritized Action Roadmap</h2>
      <p style="font-size: 0.85em; color: var(--muted); margin-bottom: 16px;">
        These are the top failed checks sorted by programmatic impact. Fix these first to yield the highest visual, speed, and conversion gains.
      </p>
      {PLAN}
    </div>

    <!-- NAP & Performance Tables -->
    {NAP_SECTION}
    {PERF_SECTION}

    <!-- Config Templates Section -->
    <div class="config-card">
      <div class="config-tab-headers">
        <button class="config-tab-btn active" onclick="switchConfigTab(this, 'robots-pane')">robots.txt</button>
        <button class="config-tab-btn" onclick="switchConfigTab(this, 'sitemap-pane')">sitemap.xml</button>
        <button class="config-tab-btn" onclick="switchConfigTab(this, 'htaccess-pane')">.htaccess Headers</button>
      </div>
      <div class="config-tab-body">
        
        <div class="config-pane active" id="robots-pane">
          <div class="config-desc">Copy this configuration into your domain's root <code>robots.txt</code> file to optimize search indexer crawl budgets.</div>
          <div class="fix-code-block">
            <div class="code-header">
              <span>robots.txt</span>
              <button class="copy-btn" onclick="copyCodeText(this, 'robots-text')">Copy Config</button>
            </div>
            <pre><code id="robots-text">{ROBOTS_TMPL}</code></pre>
          </div>
        </div>

        <div class="config-pane" id="sitemap-pane">
          <div class="config-desc">XML sitemap generated dynamically from crawled page links. Host this at <code>/sitemap.xml</code>.</div>
          <div class="fix-code-block">
            <div class="code-header">
              <span>sitemap.xml</span>
              <button class="copy-btn" onclick="copyCodeText(this, 'sitemap-text')">Copy XML</button>
            </div>
            <pre><code id="sitemap-text">{SITEMAP_TMPL}</code></pre>
          </div>
        </div>

        <div class="config-pane" id="htaccess-pane">
          <div class="config-desc">Apache configuration directives to secure session cookie transmissions and establish defense headers.</div>
          <div class="fix-code-block">
            <div class="code-header">
              <span>.htaccess</span>
              <button class="copy-btn" onclick="copyCodeText(this, 'htaccess-text')">Copy directives</button>
            </div>
            <pre><code id="htaccess-text">{HTACCESS_TMPL}</code></pre>
          </div>
        </div>

      </div>
    </div>

    <!-- Complete Audit Findings -->
    <h2 style="font-family: 'Outfit', sans-serif; font-size: 1.4em; color: var(--text); margin-bottom: 12px; margin-top: 36px;">
      🔎 Detailed Audit Findings ({TOTAL_COUNT} Checks)
    </h2>
    
    <div class="controls-bar">
      <div class="filter-tabs">
        <button class="tab-btn active" onclick="filterChecks(this, 'all')">All ({TOTAL_COUNT})</button>
        <button class="tab-btn" onclick="filterChecks(this, 'failed')">Failed ({FAILED_COUNT})</button>
        <button class="tab-btn" onclick="filterChecks(this, 'passed')">Passed ({PASSED_COUNT})</button>
        <button class="tab-btn" onclick="filterChecks(this, 'high')">Priority Failed ({HIGH_FAILED_COUNT})</button>
      </div>
      <div class="search-container">
        <span class="search-icon">🔍</span>
        <input type="text" id="check-search" class="search-input" onkeyup="searchChecks()" placeholder="Search findings...">
      </div>
    </div>

    <div class="checks-list" id="checks-list">
      {CHECKS_HTML}
    </div>

    <footer>
      Powered by <strong style="color: var(--orange);">North Web Pro</strong> — Your Guide in the Digital Wilderness
    </footer>

  </div>

  <script>
    // Expand/Collapse cards
    function toggleCard(headerElement) {
      const card = headerElement.parentElement;
      card.classList.toggle('expanded');
    }

    // Copy Code snippets
    function copyCode(buttonElement) {
      const pre = buttonElement.parentElement.nextElementSibling;
      const code = pre.querySelector('code').textContent;
      navigator.clipboard.writeText(code).then(() => {
        const originalText = buttonElement.textContent;
        buttonElement.textContent = 'Copied!';
        setTimeout(() => {
          buttonElement.textContent = originalText;
        }, 2000);
      });
    }

    // Copy configuration codes
    function copyCodeText(buttonElement, elementId) {
      const code = document.getElementById(elementId).textContent;
      navigator.clipboard.writeText(code).then(() => {
        const originalText = buttonElement.textContent;
        buttonElement.textContent = 'Copied!';
        setTimeout(() => {
          buttonElement.textContent = originalText;
        }, 2000);
      });
    }

    // Switch Server Config tabs
    function switchConfigTab(buttonElement, paneId) {
      // Deactivate all headers
      const headers = buttonElement.parentElement.querySelectorAll('.config-tab-btn');
      headers.forEach(h => h.classList.remove('active'));
      
      // Deactivate all panes
      const body = buttonElement.parentElement.nextElementSibling;
      const panes = body.querySelectorAll('.config-pane');
      panes.forEach(p => p.classList.remove('active'));
      
      // Activate selected
      buttonElement.classList.add('active');
      document.getElementById(paneId).classList.add('active');
    }

    // Filter checks list
    function filterChecks(buttonElement, filterType) {
      // Toggle active classes
      const tabs = buttonElement.parentElement.querySelectorAll('.tab-btn');
      tabs.forEach(t => t.classList.remove('active'));
      buttonElement.classList.add('active');

      const cards = document.querySelectorAll('.check-card');
      cards.forEach(card => {
        const isPassed = card.getAttribute('data-passed') === 'true';
        const severity = card.getAttribute('data-severity');
        
        let show = false;
        if (filterType === 'all') {
          show = true;
        } else if (filterType === 'failed') {
          show = !isPassed;
        } else if (filterType === 'passed') {
          show = isPassed;
        } else if (filterType === 'high') {
          show = !isPassed && (severity === 'critical' || severity === 'high');
        }

        if (show) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
      
      // Reset search filter
      document.getElementById('check-search').value = '';
    }

    // Search input checks filter
    function searchChecks() {
      const query = document.getElementById('check-search').value.toLowerCase().trim();
      const cards = document.querySelectorAll('.check-card');
      
      // Find active filter tab to respect its boundaries
      const activeTab = document.querySelector('.tab-btn.active').textContent.toLowerCase();
      let tabFilter = 'all';
      if (activeTab.includes('failed')) tabFilter = 'failed';
      else if (activeTab.includes('passed')) tabFilter = 'passed';
      else if (activeTab.includes('priority')) tabFilter = 'high';

      cards.forEach(card => {
        const isPassed = card.getAttribute('data-passed') === 'true';
        const severity = card.getAttribute('data-severity');
        const text = card.querySelector('.check-name').textContent.toLowerCase() + ' ' + 
                     card.querySelector('.category-badge').textContent.toLowerCase();

        // Respect active tab boundary
        let tabMatches = false;
        if (tabFilter === 'all') tabMatches = true;
        else if (tabFilter === 'failed') tabMatches = !isPassed;
        else if (tabFilter === 'passed') tabMatches = isPassed;
        else if (tabFilter === 'high') tabMatches = !isPassed && (severity === 'critical' || severity === 'high');

        if (tabMatches && text.includes(query)) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    }

  </script>

</body>
</html>"""

    # Format replacements using dict-based approach
    replacements = {
        "{URL}": url,
        "{SCORE}": str(score),
        "{GRADE}": grade,
        "{STROKE_OFFSET}": f"{stroke_offset:.2f}",
        "{PASSED_COUNT}": str(passed_count),
        "{FAILED_COUNT}": str(failed_count),
        "{HIGH_FAILED_COUNT}": str(high_failed_count),
        "{TOTAL_COUNT}": str(total_count),
        "{COVERAGE_SCORE}": str(score_data.get("coverage_score", "N/A")),
        "{CONFIDENCE_SCORE}": str(score_data.get("confidence_score", "N/A")),
        "{DATE}": date,
        "{GCOLOR}": gcolor,
        "{SCOLOR}": scolor,
        "{BG}": BG,
        "{CARD}": CARD,
        "{BORDER}": BORDER,
        "{ORANGE}": ORANGE,
        "{BLUE}": BLUE,
        "{TEXT}": TEXT,
        "{MUTED}": MUTED,
        "{CAT_BARS}": cat_bars,
        "{PLAN}": plan,
        "{SALES_SUMMARY}": sales_summary,
    }
    output = html_template
    for placeholder, value in replacements.items():
        output = output.replace(placeholder, value)

    # Conditional section renders
    nap_sec = f'<div class="card"><h2>📇 NAP Placement Consistency (Local SEO)</h2>{nap}</div>' if nap else ''
    perf_sec = f'<div class="card"><h2>⚡ Baseline Request Profiles</h2>{perf}</div>' if perf else ''
    output = output.replace("{NAP_SECTION}", nap_sec)
    output = output.replace("{PERF_SECTION}", perf_sec)

    output = output.replace("{CHECKS_HTML}", checks_html)
    output = output.replace("{ROBOTS_TMPL}", robots_tmpl)
    output = output.replace("{SITEMAP_TMPL}", sitemap_tmpl)
    output = output.replace("{HTACCESS_TMPL}", htaccess_tmpl)

    return output