# ADR 003: Static and Rendered Crawling

* **Status:** Accepted
* **Date:** 2026-06-21
* **Author:** Antigravity (Ponytail Coder)

## Context
Our current crawler (`crawler.py`) downloads static HTML text. While fast and lightweight, it cannot audit modern single-page applications (SPAs) or sites that dynamically inject SEO meta tags, text content, or schema via client-side JavaScript. 
However, running headless browser rendering (e.g., Playwright) for every audited page is resource-intensive, slow, and expensive.

## Decision
We will support a **Dual-Mode Crawling Strategy**:
1. **Static First:** Perform a fast static fetch by default using `curl_cffi` to analyze raw HTML, headers, response status, and identify framework markers (e.g. React/Vue/Angular scripts).
2. **Conditional Rendering:** If framework markers are detected or if the body contains minimal text compared to total script sizes, escalate the crawl to browser-rendered crawling using Playwright.
3. **Data Snapshots:** The `PageSnapshot` model will store both the raw HTML hash and the browser-rendered DOM hash, allowing checkers to explicitly audit client-side rendering issues (such as hydration mismatches or empty initial HTML).

## Consequences
* **Positive:** Accurate SEO audits for modern SPAs.
* **Positive:** Fast execution on traditional server-side rendered (SSR) websites by skipping browser rendering.
* **Negative:** Introduces Playwright as a system dependency, increasing docker image size and setup complexity.
