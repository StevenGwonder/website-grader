# Phase 2: Crawl Correctness (task.md)

This file details the active tasks for **Phase 2: Crawl Correctness** required to ensure robust, accurate web crawling, redirect tracing, sitemap index traversal, and raw-vs-rendered comparison.

Developers or autonomous agents should execute these tasks sequentially. Each task has specific instructions, file targets, and verification criteria.

---

## Strict Scope & Scope Creep Prevention (Phase 2)

The coding agent working on these tasks may **only** execute **WG-012 through WG-020**. It is strictly forbidden from implementing:
* New SEO checks (outside existing 53 check structures)
* Scoring formula rewrites (health vs coverage scoring calculations - Phase 3)
* Google Search Console, GA4, or CrUX adapters
* AI-interpretation and summary synthesis layers
* UI visual reports redesigns

---

## Task Backlog: Phase 0 (Foundation) — [COMPLETED]
* **WG-001** to **WG-006** implemented and verified. (Release Gate RG-0 passed)

---

## Task Backlog: Phase 1 (Data Contracts & Evidence) — [COMPLETED]
* **WG-007** to **WG-011** implemented and verified. (Release Gate RG-1 passed)

---

## Task Backlog: Phase 2 (Crawl Correctness)

### [WG-012: Implement URL normalization](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Create a robust URL normalizer to prevent duplicate crawl requests for near-identical paths.
* **Normalization Actions:**
  * Lowercase hostnames.
  * Strip default ports (e.g. 80, 443).
  * Remove URL fragments (`#`).
  * Remove duplicate trailing slashes (except root).
  * Remove tracking parameters (e.g. `utm_*`, `gclid`) while preserving functional parameters.
* **Target File:** Implement in `crawler.py` or a utility file.
* **Verification:** Unit tests asserting correct normalization of varying URL formats.

---

### [WG-013: Implement robust robots.txt parsing](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Parse `robots.txt` allowance/disallowance directives for custom bot user agents (including major AI search user agents).
* **Target File:** Update `crawler.py` to use a robust robots parser (such as the standard `urllib.robotparser` or similar lightweight custom parser).
* **Verification:** Assert correct block/allow evaluation against standard and complex `robots.txt` patterns.

---

### [WG-014: Implement recursive sitemap parsing](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Build a sitemap index parser to recursively gather sitemap URLs.
* **Requirements:**
  * Support sitemap index files (`<sitemapindex>`), namespaced tags, Gzip compression, and redirected sitemap paths.
  * Record all fetch outcomes (DNS error, timeout, non-200 responses) in the crawl history.
* **Target File:** Update sitemap loader in `crawler.py`.
* **Verification:** Test against local compressed sitemaps and nested index structures.

---

### [WG-015: Implement redirect traces](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Trace HTTP redirects to identify redirect paths and separate redirects from redirect chains.
* **Requirements:**
  * Track and store all hops (URLs, status codes, protocols, transitions).
  * Classify redirects: `redirect` (exactly 1 hop) vs `redirect_chain` (>1 hop) vs `loop`.
* **Target File:** Implement in `crawler.py`.
* **Verification:** Test using mock redirects and assert that single redirections are not flagged as chains.

---

### [WG-016: Implement external-link outcome classification](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Classify external links correctly to avoid false positives on link checker rules.
* **Classifications:** `access_restricted` (e.g. 403), `rate_limited` (429), `timeout`, `dns_error`, `tls_failure`, `unverified_destination`, or `valid`.
* **Target File:** Update the link checker logic in `checks/technical.py`.
* **Verification:** Mock G2/CDN endpoints returning `403` or `429` and assert that the links are reclassified rather than flagged as broken.

---

### [WG-017: Implement crawl queue and budget accounting](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Enforce crawler depth limits, page crawl limits, and time-bound loops.
* **Target File:** Update the main crawl controller in `crawler.py`.
* **Verification:** Verify that crawler stops execution exactly at budget ceilings.

---

### [WG-018: Implement static page snapshots](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Cache raw static responses and generate content hashes.
* **Target File:** Update `PageData` in `crawler.py` to store response hashes.
* **Verification:** Assert that unchanged files produce identical content hashes.

---

### [WG-019: Implement Playwright browser renderer](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Introduce browser rendering support to render JavaScript pages.
* **Requirements:**
  * Optional configuration to launch Playwright Chromium.
  * Capture final rendered DOM, console logs, screenshots, and loading errors.
  * Gracefully fall back to static fetch if browser rendering fails or is disabled.
* **Target File:** Implement a render module in `crawler.py` or a dedicated rendering helper.
* **Verification:** Render a Javascript-heavy mock SPA and check if the dynamic DOM text is retrieved.

---

### [WG-020: Build raw-versus-rendered comparison](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#crawl-correctness-phase-2)
* **Goal:** Detect disparities between original HTML and browser-rendered DOM.
* **Disparities to Trace:** Mismatched page titles, canonical tags, heading outline changes, text/word counts, or structured schemas injected at runtime.
* **Target File:** Update the check modules or crawler.
* **Verification:** Assert raw vs rendered differences are logged as findings.

---

## Release Gate RG-2 Checklist

Do not proceed beyond WG-020 until RG-2 is demonstrated. RG-2 is complete only when:
1. Crawl budget restricts are strictly enforced.
2. Sitemap index nested URLs are parsed successfully.
3. Redirect chains are distinguished from single redirects.
4. G2 and external access restricted endpoints (403/429) pass link checks as unverified/restricted.
5. URL normalization parses and cleans duplicate trailing slashes, fragments, and tracking query keys.
6. Robots rules parse correctly for custom/AI crawlers.
7. Playwright renderer runs (or falls back gracefully if disabled) and returns JavaScript-rendered DOM.
8. Raw-vs-rendered differences are tracked and output as findings.
9. All 55 existing tests pass successfully.
