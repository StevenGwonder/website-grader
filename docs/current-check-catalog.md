# Current Check Catalog

This document details all checkers currently implemented under the `checks/` directory.

---

## 1. Technical SEO (`checks/technical.py`)
Weight: 25% of overall category weighting.

| Check ID | Check Name | Severity | Description / Details |
|---|---|---|---|
| `tech_meta_title` | Meta Title | `Severity.HIGH` | Verifies presence and optimal length (30-60 characters) of `<title>`. |
| `tech_meta_desc` | Meta Description | `Severity.HIGH` | Verifies presence and optimal length (70-160 characters) of description tag. |
| `tech_headings` | H1 Heading | `Severity.HIGH` | Validates that a single `<h1>` tag exists on the page. |
| `tech_canonical` | Canonical URL | `Severity.HIGH` | Verifies the presence of a valid `<link rel="canonical">` element. |
| `tech_robots_meta` | Robots Meta Tag | `Severity.MEDIUM` | Evaluates if indexation is blocked by meta robots (`noindex`). |
| `tech_schema` | Structured Data Schema | `Severity.MEDIUM` | Counts JSON-LD script blocks on the page. |
| `tech_og_tags` | Open Graph Tags | `Severity.LOW` | Checks basic Open Graph tags (title, type, image, url). |
| `tech_twitter_cards` | Twitter Cards | `Severity.LOW` | Checks twitter card meta tags. |
| `tech_favicon` | Favicon | `Severity.LOW` | Validates presence of shortcuts/icons. |
| `tech_sitemap` | XML Sitemap | `Severity.MEDIUM` | Locates and validates basic accessibility of sitemaps. |
| `tech_robots_txt` | Robots.txt | `Severity.MEDIUM` | Checks if a robots.txt file exists. |
| `tech_broken_links` | Broken Links | `Severity.HIGH` | Checks status of outbound links (flags 4xx/5xx errors). |
| `tech_redirects` | Redirects | `Severity.HIGH` | Validates redirects of crawled internal links. |
| `tech_internal_links` | Internal Links | `Severity.MEDIUM` | Measures amount and status of internal site routing. |
| `tech_url_structure` | URL Structure | `Severity.LOW` | Audits folder depth, parameters, and casing. |
| `tech_pagination` | Pagination Link Tags | `Severity.LOW` | Identifies `rel="next"` or `rel="prev"` tags. |
| `tech_breadcrumbs` | Breadcrumbs Schema | `Severity.LOW` | Audits breadcrumb structured schema availability. |

---

## 2. Local SEO (`checks/local_seo.py`)
Weight: 20% of overall category weighting.

| Check ID | Check Name | Severity | Description / Details |
|---|---|---|---|
| `local_seo_nap_extraction` | NAP Extraction | `Severity.HIGH` | Attempts to locate Name, Address, and Phone details. |
| `local_seo_nap_consistency` | NAP Consistency | `Severity.HIGH` | Validates that NAP details match across crawled pages. |
| `local_seo_localbusiness_schema` | LocalBusiness Schema | `Severity.HIGH` | Scans structured schemas for `LocalBusiness` types. |
| `local_seo_maps_embed` | Google Maps Embed | `Severity.MEDIUM` | Detects Google Maps iframe elements. |
| `local_seo_service_area` | Service Area | `Severity.MEDIUM` | Searches for geographic area indicators on the page. |
| `local_seo_city_targeting` | City Targeting | `Severity.MEDIUM` | Audits headers and copy for target city keywords. |
| `local_seo_review_schema` | Review Schema | `Severity.MEDIUM` | Checks for `AggregateRating` schemas. |
| `local_seo_gbp_link` | Google Business Profile Link | `Severity.MEDIUM` | Checks for links pointing to Google Maps review or business pages. |

---

## 3. Performance (`checks/performance.py`)
Weight: 15% of overall category weighting.

| Check ID | Check Name | Severity | Description / Details |
|---|---|---|---|
| `performance_ttfb` | Time to First Byte | `Severity.HIGH` | Measures initial server response latency in milliseconds. |
| `performance_page_weight` | Page Weight | `Severity.MEDIUM` | Assesses sizes of HTML documents. |
| `performance_compression` | Gzip/Brotli Compression | `Severity.MEDIUM` | Audits response headers for compression types. |
| `performance_cache_headers` | Cache Control Headers | `Severity.MEDIUM` | Audits cache headers for static resources. |
| `performance_images` | Image Optimization | `Severity.MEDIUM` | Checks if image tags use modern formats (WebP/AVIF) and specify dimensions. |
| `performance_css_js` | CSS/JS Optimization | `Severity.LOW` | Audits quantities of styles and script references. |
| `performance_minification` | Minification | `Severity.LOW` | Inspects scripts and stylesheets for whitespace removal. |
| `performance_server_header` | Server Header Info | `Severity.INFO` | Identifies server software branding details exposed in headers. |

---

## 4. Content Quality (`checks/content.py`)
Weight: 15% of overall category weighting.

| Check ID | Check Name | Severity | Description / Details |
|---|---|---|---|
| `content_word_count` | Word Count | `Severity.MEDIUM` | Measures count of text content words (warns if thin/under 200 words). |
| `content_keyword_density` | Keyword Density | `Severity.LOW` | Scans for keyword repetition density percentages. |
| `content_readability` | Readability Score | `Severity.LOW` | Calculates Flesch-Kincaid reading levels. |
| `content_faq` | FAQ Schema Opportunity | `Severity.INFO` | Recommends addition of FAQ page structures. |
| `content_eeat` | E-E-A-T Signals | `Severity.MEDIUM` | Searches for trust indicators (author profiles, citations). |
| `content_uniqueness` | Content Uniqueness | `Severity.MEDIUM` | Scans text hashes for internal duplicate pages. |
| `content_title_alignment` | Title Alignment | `Severity.MEDIUM` | Compares content headers to title metadata keywords. |

---

## 5. Security (`checks/security.py`)
Weight: 10% of overall category weighting.

| Check ID | Check Name | Severity | Description / Details |
|---|---|---|---|
| `ssl` | SSL Certificate | `Severity.CRITICAL` | Confirms the homepage resolves over HTTPS. |
| `security_headers` | Security Headers | `Severity.HIGH` | Checks for security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options). |
| `mixed_content` | Mixed Content | `Severity.HIGH` | Scans for HTTP resources referenced inside HTTPS pages. |

---

## 6. Accessibility (`checks/accessibility.py`)
Weight: 10% of overall category weighting.

| Check ID | Check Name | Severity | Description / Details |
|---|---|---|---|
| `alt_text` | Image Alt Text | `Severity.HIGH` | Checks if image tags contain alt tags. |
| `form_labels` | Form Labels | `Severity.MEDIUM` | Audits form tags for associated label or aria-label attributes. |
| `heading_order` | Heading Order | `Severity.MEDIUM` | Audits strict heading order hierarchy. |
| `aria_labels` | ARIA Labels | `Severity.LOW` | Checks interactive elements with custom roles for aria-labels. |
| `skip_nav` | Skip Navigation | `Severity.LOW` | Checks for keyboard-accessible skip nav bypasses. |

---

## 7. Social & Conversion (`checks/conversion.py`)
Weight: 5% of overall category weighting.

| Check ID | Check Name | Severity | Description / Details |
|---|---|---|---|
| `social_links` | Social Media Links | `Severity.LOW` | Detects pointers to popular social platforms. |
| `analytics` | Analytics Setup | `Severity.MEDIUM` | Searches for tracking code signatures (GTM, GA4, Meta pixel). |
| `cta_elements` | Call to Action Elements | `Severity.MEDIUM` | Audits availability of actions (forms, contact tel, schedulers). |
| `trust_signals` | Trust Signals | `Severity.MEDIUM` | Detects testimonials, certifications, or security badges. |
| `contact_form` | Contact Form | `Severity.MEDIUM` | Verifies presence of a visible contact form element. |
