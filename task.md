# Phase 1: Data Contracts & Evidence (task.md)

This file details the active tasks for **Phase 1: Data Contracts and Evidence** required to implement rules metadata, enums, evidence schemas, and deduplication logic.

Developers or autonomous agents should execute these tasks sequentially. Each task has specific instructions, file targets, and verification criteria.

---

## Strict Scope & Scope Creep Prevention (Phase 1)

The coding agent working on these tasks may **only** execute **WG-007 through WG-011**. It is strictly forbidden from implementing:
* New SEO checks
* Crawl engine rewrites (Playwright, URL normalization, redirect traces)
* Google Search Console, GA4, or CrUX adapters
* Lighthouse or axe-core integrations
* Visual report UI design overhauls

*The coding agent is building the data and diagnosis layers, not the crawling or presentation layers.*

---

## Task Backlog: Phase 0 (Foundation) — [COMPLETED]
* **WG-001:** Inventory the repository. (Completed)
* **WG-002:** Reproduce the current SEO.com audit from a frozen fixture. (Completed)
* **WG-003:** Create known-defect regression tests. (Completed)
* **WG-004:** Create Architecture Decision Records (ADRs). (Completed)
* **WG-005:** Create Pydantic output models. (Completed)
* **WG-006:** Add schema migration support. (Completed)

**Release Gate RG-0:** Demonstrated. Frozen audit reproduces baseline scores net-free.

---

## Task Backlog: Phase 1 (Data Contracts & Evidence)

### [WG-007: Build the rule registry](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#evidence--rule-registry-phase-1)
* **Goal:** Create a centralized registry mapping rule IDs to metadata. Do not hard-code rules inside checks.
* **Registry Metadata Fields:**
  * `check_id` (string)
  * `version` (string)
  * `category` (string)
  * `default_weight` (integer)
  * `default_severity` (string)
  * `applicability` (list/object mapping site and page types)
  * `recommendation_template` (string template)
  * `documentation_references` (list of URLs/specs)
  * `deprecation_status` (boolean)
* **Target File:** Implement in `checks/registry.py` or within `checks/base.py`.
* **Verification:** Unit tests to verify that checking classes can look up metadata using a `check_id`.

---

### [WG-008: Implement finding states](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#evidence--rule-registry-phase-1)
* **Goal:** Evolve the check runner to return findings with the correct status enums.
* **Requirements:**
  * Transition all 53 existing checks under [checks/](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/checks) to map their output to `FindingStatus` enum values (`PASS`, `FAIL`, `WARNING`, `NOT_APPLICABLE`, `INFORMATIONAL`, etc.) instead of returning a simple boolean `passed`.
  * Ensure a missing check does not raise exceptions but outputs `UNVERIFIED` or `ERROR` gracefully.
* **Target Files:** Update `checks/base.py`, `checks/*.py`, and the scoring engine in `scoring.py`.
* **Verification:** Run `pytest` and verify that the output structure of all audit tasks formats using the `FindingStatus` string enums.

---

### [WG-009: Implement evidence persistence](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#evidence--rule-registry-phase-1)
* **Goal:** Ensure every failing (`FAIL` or `WARNING`) diagnostic creates traceable, immutable `Evidence` records.
* **Requirements:**
  * In the check execution blocks, extract details (such as tag properties, CSS selectors, or HTTP status responses) and map them to `Evidence` models in `models.py`.
  * Link these evidence lists directly to the generated findings.
* **Target Files:** Update check files under `checks/`.
* **Verification:** Assert that testing fixtures (e.g. sitemap or canonical failures) populate the `evidence` field in `CheckResult` with valid selectors and values.

---

### [WG-010: Add audit coverage metadata](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#evidence--rule-registry-phase-1)
* **Goal:** Implement auditing metrics representing the completeness of the crawl.
* **Reported Metrics:**
  * Discovered URLs
  * Crawled URLs
  * Excluded URLs
  * Fetch failures
  * Available external integrations (GSC, GA4, CrUX etc. - currently marked as unavailable/stubbed)
  * Count of evaluated checks vs unavailable checks
* **Target File:** Implement in `crawler.py` and `grader.py`.
* **Verification:** Assert that the CLI output and JSON schemas populate the metadata block correctly.

---

### [WG-011: Add finding deduplication](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md#evidence--rule-registry-phase-1)
* **Goal:** Group identical violations originating from the same templates/components.
* **Logic:**
  * Match violations using Check ID and template signatures (or component selector patterns, like footer navigation).
  * Consolidate duplicate page findings into a single consolidated report card referencing multiple affected URLs, preventing report bloat.
* **Target File:** Implement a deduplicator helper in `scoring.py` or a helper module.
* **Verification:** Assert that running checks on multiple mocked layout templates groups the identical findings correctly.

---

## Release Gate RG-1 Checklist

Do not proceed beyond WG-011 until RG-1 is demonstrated. RG-1 is complete only when:
1. Every rule executes through the rules registry lookup.
2. The check runner outputs findings using `FindingStatus` enums.
3. Every failing finding lists at least one traceable, immutable `Evidence` record.
4. Crawl metadata records are fully populated.
5. Template/component findings are deduplicated.
6. Existing 33 unit tests, 11 defect regression tests, and all new data contract checks pass.
7. Unverified findings are correctly reclassified instead of flagged as hard failures.
