# ADR 001: Evidence-First Audit Findings

* **Status:** Accepted
* **Date:** 2026-06-21
* **Author:** Antigravity (Ponytail Coder)

## Context
In the current implementation of the website grader, checkers evaluate pages and return a binary `passed` flag along with a string `detail`. There is no structured record of the specific evidence (such as a CSS selector, an HTTP response header, a specific line of code, or a structured JSON path) that triggered the check's result. This lack of data prevents:
1. Explainability: The user has to trust the string description without seeing the source.
2. Verification: The system cannot easily re-verify a specific finding without crawling the entire site again.
3. Automated fixes: LLM integration or codegen tools lack direct context to write accurate fixes.

## Decision
We will transition to an **Evidence-First** framework where every check finding must link directly to one or more traceable, immutable `Evidence` records.

The `Evidence` schema will include:
* `evidence_id`: Unique identifier for the evidence trace.
* `url`: The source URL where the evidence was captured.
* `locator_type`: The lookup method (e.g. `css_selector`, `xpath`, `http_header`, `json_path`, `regex_match`).
* `locator_value`: The query value (e.g. `head > title`, `content-encoding`).
* `captured_value`: The actual string, snippet, or data value captured at the locator.
* `context_snippet`: Optional surrounding context (e.g. adjacent HTML lines) to assist visualizers or developers.

Checkers must populate the `Evidence` records as part of the `Finding` output.

## Consequences
* **Positive:** Complete explainability. Users and automated verification agents can trace findings directly back to source selectors or headers.
* **Positive:** Enables targeted re-audits (only reload the specific URLs and query the exact locators).
* **Negative:** Checkers must be updated to return structured evidence details, adding minor complexity to rule writing.
