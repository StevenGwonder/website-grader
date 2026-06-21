# Phase 3: Applicability & Scoring (task.md)

This file details the active tasks for **Phase 3: Applicability and Scoring** required to establish site and page classifications, run check applicability overlays, and calculate separate scores for health, coverage, confidence, and opportunity.

Developers or autonomous agents should execute these tasks sequentially. Each task has specific instructions, file targets, and verification criteria.

---

## Strict Scope & Scope Creep Prevention (Phase 3)

The coding agent working on these tasks may **only** execute **WG-021 through WG-026**. It is strictly forbidden from implementing:
* New SEO checks (outside existing 53 check structures)
* Lighthouse or axe-core automated execution
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

## Task Backlog: Phase 2 (Crawl Correctness) — [COMPLETED]
* **WG-012** to **WG-020** implemented and verified. (Release Gate RG-2 passed)

---

## Task Backlog: Phase 3 (Applicability & Scoring)

### [WG-021: Implement page-type heuristics](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#classification--applicability-phase-3)
* **Goal:** Classify pages into specific types using path patterns, content signals, and layout structures.
* **Requirements:**
  * Support page types: `homepage`, `service`, `location`, `contact`, `about`, `blog_article`, `ecommerce_product`, `ecommerce_category`, `utility`, `policy`, `other`.
  * Extract heuristics: check page URLs (e.g. `/contact`, `/about`), presence of CTA contact forms, page elements, or schema tags (e.g. `Product` schema $\rightarrow$ `ecommerce_product`).
  * Support user profile configurations as overrides.
* **Target File:** Implement a page classifier in `classifiers.py` or update `crawler.py`.
* **Verification:** Unit tests verifying that various mock URLs and HTML inputs resolve to correct page types.

---

### [WG-022: Implement site-type heuristics](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#classification--applicability-phase-3)
* **Goal:** Classify the overall site intent based on crawl characteristics.
* **Requirements:**
  * Classify site types: `local_service_business`, `local_storefront`, `multi_location_business`, `national_saas`, `ecommerce`, `publisher`, `corporate`, `other`.
  * Heuristic signals: schema occurrences (e.g. `LocalBusiness` vs `Product`), directory patterns, contact details, map embeds, and URL patterns.
  * Support manual user configuration overrides in the profile request.
* **Target File:** Implement a site classifier in `classifiers.py`.
* **Verification:** Verify that mock crawls containing map embeds and local phone numbers classify as a local business.

---

### [WG-023: Implement location-model classification](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#classification--applicability-phase-3)
* **Goal:** Categorize the local operations model of the target site to prevent false positive Local SEO audits.
* **Location Models:** `storefront` (physical address required), `service_area` (address optional, region required), `multi_location` (requires branch links/pages), `national_no_local` (Local SEO checks skipped entirely).
* **Target File:** Implement in `classifiers.py` as part of the profiling loop.
* **Verification:** Assert that a national SaaS profile returns `national_no_local` and an address-less plumbing profile returns `service_area`.

---

### [WG-024: Add applicability evaluation](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#classification--applicability-phase-3)
* **Goal:** Filter checks dynamically based on the site profile and page classification.
* **Requirements:**
  * Query the `applies_to_site_types` and `applies_to_page_types` parameters from `registry.py`.
  * If a check is not applicable to the site profile, mark the check outcome as `status = FindingStatus.NOT_APPLICABLE` and assign an applicability reason (e.g., "Local SEO checks skipped for National SaaS profiles").
* **Target File:** Update the check runner logic in `checks/base.py` and `grader.py`.
* **Verification:** Verify that local business map/address checks return `NOT_APPLICABLE` on national SaaS mock crawls.

---

### [WG-025: Replace the current scoring formula](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#classification--applicability-phase-3)
* **Goal:** Calculate and output the four separate scores defined in the scoring contract: Health, Coverage, Confidence, and Opportunity Potential.
* **Requirements:**
  * **Health Score:** Calculate solely from applicable and evaluated checks. Ensure `NOT_APPLICABLE` and `INFORMATIONAL` status findings do not impact the score.
  * **Coverage Score:** Ratio of evaluated applicable check weights against all potentially applicable check weights. Unconnected APIs (GSC, GA4, CrUX) lower coverage, not health.
  * **Confidence Score:** Factor in deterministic checks accuracy, static/rendered agreement, and classification confidence.
  * **Opportunity Potential:** Potential upside based on prevalence of failures and ease of fixing.
* **Target File:** Evolve `scoring.py`.
* **Verification:** Assert that site scores are calculated and return the correct independent percentages.

---

### [WG-026: Implement contextual severity](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#classification--applicability-phase-3)
* **Goal:** Adjust diagnostic check severity scale dynamically based on page type, page depth, and classification features (e.g. canonical mismatch is high-priority on homepage but low-priority on a policy utility page).
* **Target File:** Update the check runner and checks metadata loader in `checks/base.py`.
* **Verification:** Assert that checks executed on utility template pages output adjusted, lower priority ratings.

---

## Release Gate RG-3 Checklist

Do not proceed beyond WG-026 until RG-3 is demonstrated. RG-3 is complete only when:
1. `classifiers.py` exists and correctly infers site profile.
2. Page-type classification correctly categorizes mock URLs.
3. Location models are classified (storefront, service-area, multi-location, national).
4. Unconditional Local SEO penalties are removed for SaaS/national profiles (they resolve as `NOT_APPLICABLE` and return 100/pass scores).
5. Scoring engine calculates four separate scores (Health, Coverage, Confidence, Opportunity) instead of a single merged number.
6. Checkrunner updates severity ratings contextually.
7. Existing 62 tests run and pass successfully.
