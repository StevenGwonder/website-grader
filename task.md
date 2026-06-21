# Next Steps Task List (task.md)

This file details the initial kickoff tasks (**Phase 0: Foundation**) required to evolve the website grader codebase into the Website Intelligence Platform.

Developers or autonomous agents should execute these tasks sequentially. Each task has specific instructions, file targets, and verification criteria.

---

## Strict Scope & Scope Creep Prevention

The coding agent working on these tasks may **only** execute **WG-001 through WG-006**. It is strictly forbidden from implementing:
* New SEO checks
* New scoring formulas
* Playwright rendering
* Lighthouse integration
* axe-core accessibility checks
* Google Search Console or Google Analytics 4 adapters
* AI search/GEO visibility checks
* Local SEO category rewrites
* Report UI redesigns
* Multi-tenant or billing modules

*The coding agent is building the foundation, not the cathedral. Humans already tried tower-building once and it produced JavaScript frameworks.*

---

## Task Backlog: Phase 0 (Foundation)

### [WG-001: Inventory the repository](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#foundation-phase-0)
* **Goal:** Document the entry points, existing checks, scoring formulas, data flows, and current test coverage. Do not change any execution code.
* **Target Files to Create:**
  * `docs/current-state.md`
  * `docs/current-check-catalog.md`
  * `docs/current-data-flow.md`
  * `docs/current-output-contract.md`
* **Verification:** Verify that all existing check files under [checks/](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/checks) are cataloged.

---

### [WG-002: Reproduce the current SEO.com audit](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#foundation-phase-0)
* **Goal:** Create a frozen mock HTML and response fixture representing the current audit results for `seo.com` so we can run regression checks.
* **Fixture Checklist:** The frozen fixture must include:
  1. `manifest.json` mapping URLs to mock files.
  2. The original five crawled URLs.
  3. Raw HTML fixture per URL.
  4. Rendered DOM fixture per URL if available, or explicit unavailable marker.
  5. HTTP status and headers per URL.
  6. Redirect traces.
  7. Robots.txt response fixture.
  8. Sitemap candidate response fixtures.
  9. External G2 `403` response fixture.
  10. Expected legacy audit JSON.
  11. Expected current HTML report if generated.
  12. Test helper that runs the current engine without live network access.
* **Target Directory:** `tests/fixtures/seo_com_frozen/`
* **Verification:** The existing audit engine runs against this fixture and produces the expected baseline JSON/HTML report without hitting network endpoints.

---

### [WG-003: Create known-defect regression tests](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#foundation-phase-0)
* **Goal:** Create test fixtures and failing test cases for the 11 baseline bugs identified in [PRD.md](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#3-existing-baseline-problems-to-correct):
  1. Sitemap index or invalid sitemap endpoint reported as "0 URLs" instead of accurately classified.
  2. External `403 Forbidden` classified as a broken link instead of access-restricted or unverified.
  3. A single-hop redirect classified as a redirect chain.
  4. Business name extracted solely from the `<title>` tag, creating false NAP mismatch.
  5. National, SaaS, ecommerce, or non-local website penalized with Local SEO zero.
  6. Obsolete FAQ schema advice presented as a Google rich-result opportunity.
  7. Structured-data audit counts JSON-LD script blocks instead of parsing entities, `@graph`, and supported feature eligibility.
  8. Keyword-density fixed-percentage rule flags repetition without excluding boilerplate, nav, footer, or brand/service context.
  9. Readability score treated as a failure without page-type, audience, industry, or text-region context.
  10. Accessibility tests count missing attributes instead of computed accessible names, valid labels, landmarks, focus behavior, and component-level grouping.
  11. Unsafe generated fix code produces fictional addresses, phone numbers, ratings, review counts, map coordinates, or business hours.
* **Target Files:** Create or update `tests/test_defects.py` (or write inside [test_technical.py](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/test_technical.py)).
* **Verification:** Run `pytest tests/test_defects.py`. The tests may intentionally fail against the current codebase. They exist to prove the defects before fixing them.

---

### [WG-004: Create Architecture Decision Records (ADRs)](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#foundation-phase-0)
* **Goal:** Document the four foundational design decisions outlined in the specifications:
  * `docs/adr/001-evidence-first.md`: Design of immutable evidence tracking.
  * `docs/adr/002-applicability-aware-scoring.md`: Transitioning to health, coverage, confidence, and opportunity.
  * `docs/adr/003-static-and-rendered-crawling.md`: Layout snapshotting rules (raw vs browser-rendered).
  * `docs/adr/004-ai-as-interpretation-layer.md`: AI governance and cost/token limits.
* **Target Directory:** `docs/adr/`
* **Verification:** Check files are created with standard ADR templates (Status, Context, Decision, Consequences).

---

### [WG-005: Create Pydantic output models](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#foundation-phase-0)
* **Goal:** Implement the data models defined in `AGENT.md` using Pydantic.
* **Target File:** Create `models.py` in the root of the project.
* **Model Requirements:** Create initial Pydantic models for:
  * `AuditRun`
  * `SiteProfile`
  * `PageSnapshot`
  * `Evidence`
  * `Finding`
  * `Recommendation`
  * `ScoreSummary`
  * `LegacyAuditReport`
  * `MigrationResult`
* **Technical Constraints:**
  * Use `schema_version = "2.0.0"`.
  * Use `Field(default_factory=...)` for timestamps, IDs, and lists.
  * Do not use mutable defaults like `[]` or direct list assignments.
  * Do not use `datetime.utcnow()` directly as a default value (use callable factories).
* **Verification:** Add basic validation test in `tests/test_models.py` to assert correct parsing of these objects.

---

### [WG-006: Add schema migration support](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#foundation-phase-0)
* **Goal:** Create a serialization layer to map current unstructured JSON formats to the new Pydantic schema structure.
* **Target File:** Implement a serializer function in `models.py` or `scoring.py`.
* **Verification:** Run the existing grader, run the serializer, and assert that the resulting output matches the schema version `2.0.0` format.

---

## Release Gate RG-0 Checklist

Do not proceed beyond WG-006 until RG-0 is demonstrated. RG-0 is complete only when:
1. `docs/current-state.md` exists.
2. `docs/current-check-catalog.md` exists.
3. `docs/current-data-flow.md` exists.
4. `docs/current-output-contract.md` exists.
5. Existing entry points are documented.
6. Existing check files are cataloged.
7. Current scoring formula is documented.
8. Current report schema is documented.
9. SEO.com baseline audit can run from frozen fixtures without network calls.
10. Known-defect regression tests exist (for all 11 issues).
11. Known-defect tests either fail against current behavior or are marked expected-fail with a reason.
12. ADR files exist for evidence-first, applicability-aware scoring, static/rendered crawling, and AI-as-interpretation-layer.
13. Pydantic schema file exists (`models.py`).
14. Schema validation tests exist.
15. A legacy-to-v2 serializer or migration stub exists.
16. No production audit logic has been modified except where needed to make the fixture runner possible.
