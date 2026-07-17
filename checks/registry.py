from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class RuleMetadata(BaseModel):
    check_id: str
    name: str
    version: str = "1.0.0"
    category: str
    default_weight: int
    default_severity: str  # "critical", "high", "medium", "low", "info"
    applicability: Dict[str, Any]
    recommendation_template: str
    documentation_references: List[str]
    deprecation_status: bool = False

RULE_REGISTRY: Dict[str, RuleMetadata] = {
    # Technical SEO
    "tech_meta_title": RuleMetadata(
        check_id="tech_meta_title",
        name="Meta Title",
        category="Technical SEO",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Title should be 30-60 chars, include target keywords, and be unique per page.",
        documentation_references=["https://developers.google.com/search/docs/appearance/title-link"]
    ),
    "tech_meta_desc": RuleMetadata(
        check_id="tech_meta_desc",
        name="Meta Description",
        category="Technical SEO",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Description should be 120-160 chars with a compelling CTR-optimized summary.",
        documentation_references=["https://developers.google.com/search/docs/appearance/snippet"]
    ),
    "tech_headings": RuleMetadata(
        check_id="tech_headings",
        name="Heading Hierarchy",
        category="Technical SEO",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Use exactly one H1 per page. Don't skip heading levels (H1→H3 is bad). Use H2 for sections, H3 for subsections.",
        documentation_references=["https://html.spec.whatwg.org/multipage/sections.html#headings-and-sections"]
    ),
    "tech_canonical": RuleMetadata(
        check_id="tech_canonical",
        name="Canonical URL",
        category="Technical SEO",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Verify the presence of a valid <link rel=\"canonical\"> element.",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"]
    ),
    "tech_robots_meta": RuleMetadata(
        check_id="tech_robots_meta",
        name="Robots Meta Tag",
        category="Technical SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Evaluates if indexation is blocked by meta robots (noindex).",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag"]
    ),
    "tech_schema": RuleMetadata(
        check_id="tech_schema",
        name="Structured Data Schema",
        category="Technical SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Counts JSON-LD script blocks on the page.",
        documentation_references=["https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data"]
    ),
    "tech_og_tags": RuleMetadata(
        check_id="tech_og_tags",
        name="Open Graph Tags",
        category="Technical SEO",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Checks basic Open Graph tags (title, type, image, url).",
        documentation_references=["https://ogp.me/"]
    ),
    "tech_twitter_cards": RuleMetadata(
        check_id="tech_twitter_cards",
        name="Twitter Cards",
        category="Technical SEO",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Checks twitter card meta tags.",
        documentation_references=["https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards"]
    ),
    "tech_favicon": RuleMetadata(
        check_id="tech_favicon",
        name="Favicon",
        category="Technical SEO",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Validates presence of shortcuts/icons.",
        documentation_references=["https://developers.google.com/search/docs/appearance/favicon-in-search"]
    ),
    "tech_sitemap": RuleMetadata(
        check_id="tech_sitemap",
        name="XML Sitemap",
        category="Technical SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Locates and validates sitemaps indexing.",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview"]
    ),
    "tech_robots_txt": RuleMetadata(
        check_id="tech_robots_txt",
        name="Robots.txt",
        category="Technical SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Checks if a robots.txt file exists.",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/robots/intro"]
    ),
    "tech_broken_links": RuleMetadata(
        check_id="tech_broken_links",
        name="Broken Links",
        category="Technical SEO",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Checks status of outbound links (flags 4xx/5xx errors).",
        documentation_references=["https://html.spec.whatwg.org/multipage/links.html"]
    ),
    "tech_redirects": RuleMetadata(
        check_id="tech_redirects",
        name="Redirects",
        category="Technical SEO",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Validates redirects of crawled internal links.",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/301-redirects"]
    ),
    "tech_internal_links": RuleMetadata(
        check_id="tech_internal_links",
        name="Internal Links",
        category="Technical SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Measures amount and status of internal site routing.",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/links-explained"]
    ),
    "tech_url_structure": RuleMetadata(
        check_id="tech_url_structure",
        name="URL Structure",
        category="Technical SEO",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Audits folder depth, parameters, and casing.",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/url-structure"]
    ),
    "tech_pagination": RuleMetadata(
        check_id="tech_pagination",
        name="Pagination Link Tags",
        category="Technical SEO",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Identifies rel=\"next\" or rel=\"prev\" tags.",
        documentation_references=["https://developers.google.com/search/blog/2019/03/spring-cleaning-relnextprev"]
    ),
    "tech_breadcrumbs": RuleMetadata(
        check_id="tech_breadcrumbs",
        name="Breadcrumbs Schema",
        category="Technical SEO",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Audits breadcrumb structured schema availability.",
        documentation_references=["https://developers.google.com/search/docs/appearance/structured-data/breadcrumb"]
    ),

    # Local SEO
    "local_seo_nap_extraction": RuleMetadata(
        check_id="local_seo_nap_extraction",
        name="NAP Extraction",
        category="Local SEO",
        default_weight=40,
        default_severity="critical",
        applicability={"site_types": ["local"], "page_types": ["*"]},
        recommendation_template="Ensure your business Name, Address, and Phone are clearly visible on the page.",
        documentation_references=["https://developers.google.com/search/docs/appearance/structured-data/local-business"]
    ),
    "local_seo_nap_consistency": RuleMetadata(
        check_id="local_seo_nap_consistency",
        name="NAP Consistency",
        category="Local SEO",
        default_weight=40,
        default_severity="critical",
        applicability={"site_types": ["local"], "page_types": ["*"]},
        recommendation_template="Ensure consistent NAP data across all pages.",
        documentation_references=["https://support.google.com/business/answer/3038177"]
    ),
    "local_seo_localbusiness_schema": RuleMetadata(
        check_id="local_seo_localbusiness_schema",
        name="LocalBusiness Schema",
        category="Local SEO",
        default_weight=40,
        default_severity="critical",
        applicability={"site_types": ["local"], "page_types": ["*"]},
        recommendation_template="Add LocalBusiness structured data to your homepage.",
        documentation_references=["https://schema.org/LocalBusiness"]
    ),
    "local_seo_maps_embed": RuleMetadata(
        check_id="local_seo_maps_embed",
        name="Google Maps Embed",
        category="Local SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["local"], "page_types": ["*"]},
        recommendation_template="Embed a Google Map on your contact or homepage.",
        documentation_references=["https://developers.google.com/maps/documentation/embed/get-started"]
    ),
    "local_seo_service_area": RuleMetadata(
        check_id="local_seo_service_area",
        name="Service Area",
        category="Local SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["local"], "page_types": ["*"]},
        recommendation_template="Add service area information if you serve specific geographic areas.",
        documentation_references=["https://support.google.com/business/answer/9157481"]
    ),
    "local_seo_city_targeting": RuleMetadata(
        check_id="local_seo_city_targeting",
        name="City Targeting",
        category="Local SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["local"], "page_types": ["*"]},
        recommendation_template="Include target city name in your headings and page content.",
        documentation_references=["https://developers.google.com/search/docs/fundamentals/seo-starter-guide"]
    ),
    "local_seo_review_schema": RuleMetadata(
        check_id="local_seo_review_schema",
        name="Review Schema",
        category="Local SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["local"], "page_types": ["*"]},
        recommendation_template="Implement product or business review schema to show rating stars.",
        documentation_references=["https://developers.google.com/search/docs/appearance/structured-data/review-snippet"]
    ),
    "local_seo_gbp_link": RuleMetadata(
        check_id="local_seo_gbp_link",
        name="Google Business Profile Link",
        category="Local SEO",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["local"], "page_types": ["*"]},
        recommendation_template="Link to your Google Business Profile to build local authority.",
        documentation_references=["https://www.google.com/business/"]
    ),

    # Performance
    "performance_ttfb": RuleMetadata(
        check_id="performance_ttfb",
        name="Time to First Byte",
        category="Performance",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Improve server response time by caching and optimizing resources.",
        documentation_references=["https://web.dev/ttfb/"]
    ),
    "performance_page_weight": RuleMetadata(
        check_id="performance_page_weight",
        name="Page Weight",
        category="Performance",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Reduce page weight by optimizing resources and removing unneeded code.",
        documentation_references=["https://web.dev/total-byte-weight/"]
    ),
    "performance_compression": RuleMetadata(
        check_id="performance_compression",
        name="Gzip/Brotli Compression",
        category="Performance",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Enable Gzip or Brotli compression on your web server.",
        documentation_references=["https://web.dev/uses-text-compression/"]
    ),
    "performance_cache_headers": RuleMetadata(
        check_id="performance_cache_headers",
        name="Cache Control Headers",
        category="Performance",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Set long-term cache headers for static assets.",
        documentation_references=["https://web.dev/uses-long-cache-ttl/"]
    ),
    "performance_images": RuleMetadata(
        check_id="performance_images",
        name="Image Optimization",
        category="Performance",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Use modern image formats and specify dimensions for images.",
        documentation_references=["https://web.dev/serve-images-in-modern-formats/"]
    ),
    "performance_css_js": RuleMetadata(
        check_id="performance_css_js",
        name="CSS/JS Optimization",
        category="Performance",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Combine and minimize stylesheet and script references.",
        documentation_references=["https://web.dev/minify-css/"]
    ),
    "performance_minification": RuleMetadata(
        check_id="performance_minification",
        name="Minification",
        category="Performance",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Minify HTML, CSS, and JS files.",
        documentation_references=["https://web.dev/minify-javascript/"]
    ),
    "performance_server_header": RuleMetadata(
        check_id="performance_server_header",
        name="Server Header Info",
        category="Performance",
        default_weight=5,
        default_severity="info",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Remove detailed server software branding from headers.",
        documentation_references=["https://owasp.org/www-project-secure-headers/"]
    ),

    # Content Quality
    "content_word_count": RuleMetadata(
        check_id="content_word_count",
        name="Word Count",
        category="Content Quality",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Ensure pages have a healthy word count (at least 200 words of rich content).",
        documentation_references=["https://developers.google.com/search/docs/fundamentals/creating-helpful-content"]
    ),
    "content_keyword_density": RuleMetadata(
        check_id="content_keyword_density",
        name="Keyword Density",
        category="Content Quality",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Write naturally instead of stuffing keywords repeatedly.",
        documentation_references=["https://developers.google.com/search/docs/essentials/spam-policies#keyword-stuffing"]
    ),
    "content_readability": RuleMetadata(
        check_id="content_readability",
        name="Readability Score",
        category="Content Quality",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Improve readability to match your target audience.",
        documentation_references=["https://www.w3.org/WAI/WCAG21/Understanding/reading-level.html"]
    ),
    "content_faq": RuleMetadata(
        check_id="content_faq",
        name="FAQ Schema Opportunity",
        category="Content Quality",
        default_weight=5,
        default_severity="info",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Add FAQ content structure if appropriate for user queries.",
        documentation_references=["https://developers.google.com/search/docs/appearance/structured-data/faqpage"]
    ),
    "content_eeat": RuleMetadata(
        check_id="content_eeat",
        name="E-E-A-T Signals",
        category="Content Quality",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Add author profiles, trust badges, and outbound source citations.",
        documentation_references=["https://developers.google.com/search/blog/2022/12/google-search-essentials-updates"]
    ),
    "content_uniqueness": RuleMetadata(
        check_id="content_uniqueness",
        name="Content Uniqueness",
        category="Content Quality",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Avoid duplicate pages within your site.",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/avoid-duplicate-content"]
    ),
    "content_title_alignment": RuleMetadata(
        check_id="content_title_alignment",
        name="Title Alignment",
        category="Content Quality",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Align page headings with title tag topics.",
        documentation_references=["https://developers.google.com/search/docs/fundamentals/seo-starter-guide#use-headings-sparingly"]
    ),

    # Security
    "ssl": RuleMetadata(
        check_id="ssl",
        name="SSL Certificate",
        category="Security",
        default_weight=40,
        default_severity="critical",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Serve your site over HTTPS to encrypt data and build trust.",
        documentation_references=["https://developers.google.com/search/docs/crawling-indexing/https-bypass-sitemaps"]
    ),
    "security_headers": RuleMetadata(
        check_id="security_headers",
        name="Security Headers",
        category="Security",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Add missing security headers to protect against common web vulnerabilities.",
        documentation_references=["https://owasp.org/www-project-secure-headers/"]
    ),
    "mixed_content": RuleMetadata(
        check_id="mixed_content",
        name="Mixed Content",
        category="Security",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Replace all HTTP resources with HTTPS versions to avoid security warnings.",
        documentation_references=["https://web.dev/what-is-mixed-content/"]
    ),

    # Accessibility
    "alt_text": RuleMetadata(
        check_id="alt_text",
        name="Image Alt Text",
        category="Accessibility",
        default_weight=30,
        default_severity="high",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Add descriptive alt text to all images.",
        documentation_references=["https://www.w3.org/WAI/tutorials/images/"]
    ),
    "form_labels": RuleMetadata(
        check_id="form_labels",
        name="Form Labels",
        category="Accessibility",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Add labels to all form inputs using <label> or aria-label.",
        documentation_references=["https://www.w3.org/WAI/tutorials/forms/labels/"]
    ),
    "heading_order": RuleMetadata(
        check_id="heading_order",
        name="Heading Order",
        category="Accessibility",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Maintain logical heading hierarchies.",
        documentation_references=["https://www.w3.org/WAI/tutorials/page-structure/headings/"]
    ),
    "aria_labels": RuleMetadata(
        check_id="aria_labels",
        name="ARIA Labels",
        category="Accessibility",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Check interactive elements with custom roles for aria-labels.",
        documentation_references=["https://www.w3.org/TR/wai-aria-1.1/"]
    ),
    "skip_nav": RuleMetadata(
        check_id="skip_nav",
        name="Skip Navigation",
        category="Accessibility",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Add a skip navigation link for screen readers.",
        documentation_references=["https://webaim.org/techniques/skipnav/"]
    ),

    # Social & Conversion
    "social_links": RuleMetadata(
        check_id="social_links",
        name="Social Media Links",
        category="Social & Conversion",
        default_weight=10,
        default_severity="low",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Add links to your social media profiles.",
        documentation_references=["https://developers.google.com/search/docs/appearance/structured-data/social-profile"]
    ),
    "analytics": RuleMetadata(
        check_id="analytics",
        name="Analytics Setup",
        category="Social & Conversion",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Set up analytics tracking to monitor traffic.",
        documentation_references=["https://support.google.com/analytics/answer/9304153"]
    ),
    "cta_elements": RuleMetadata(
        check_id="cta_elements",
        name="Call to Action Elements",
        category="Social & Conversion",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Ensure clear calls to action (buttons, forms, links).",
        documentation_references=["https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html"]
    ),
    "trust_signals": RuleMetadata(
        check_id="trust_signals",
        name="Trust Signals",
        category="Social & Conversion",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Display trust badges, certifications, or testimonials.",
        documentation_references=["https://www.w3.org/WAI/WCAG21/Understanding/trustworthy.html"]
    ),
    "contact_form": RuleMetadata(
        check_id="contact_form",
        name="Contact Form",
        category="Social & Conversion",
        default_weight=20,
        default_severity="medium",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Include a contact form to capture leads.",
        documentation_references=["https://www.w3.org/WAI/tutorials/forms/"]
    ),

    # External Intelligence
    "ext_mozilla_observatory": RuleMetadata(
        check_id="ext_mozilla_observatory",
        name="Mozilla Observatory (Security Headers)",
        category="External Intelligence",
        default_weight=10,
        default_severity="info",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Improve security headers to protect against common web vulnerabilities.",
        documentation_references=["https://observatory.mozilla.org/"]
    ),
    "ext_crt_sh": RuleMetadata(
        check_id="ext_crt_sh",
        name="SSL Certificate History (crt.sh)",
        category="External Intelligence",
        default_weight=5,
        default_severity="info",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Ensure SSL certificates are valid and not expired.",
        documentation_references=["https://crt.sh/"]
    ),
    "ext_hsts_preload": RuleMetadata(
        check_id="ext_hsts_preload",
        name="HSTS Preload List",
        category="External Intelligence",
        default_weight=5,
        default_severity="info",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Submit domain to HSTS Preload for automatic HTTPS enforcement.",
        documentation_references=["https://hstspreload.org/"]
    ),
    "ext_whatweb": RuleMetadata(
        check_id="ext_whatweb",
        name="Technology Stack (WhatWeb)",
        category="External Intelligence",
        default_weight=5,
        default_severity="info",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Install WhatWeb CLI for technology stack detection.",
        documentation_references=["https://github.com/urbanadventurer/WhatWeb"]
    ),
    "ext_wappalyzer": RuleMetadata(
        check_id="ext_wappalyzer",
        name="Technology Stack (Wappalyzer)",
        category="External Intelligence",
        default_weight=5,
        default_severity="info",
        applicability={"site_types": ["*"], "page_types": ["*"]},
        recommendation_template="Install Wappalyzer Python package for technology stack detection.",
        documentation_references=["https://github.com/aliasio/wappalyzer"]
    ),
}

def get_rule_metadata(check_id: str) -> Optional[RuleMetadata]:
    return RULE_REGISTRY.get(check_id)
