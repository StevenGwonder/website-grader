# Current State of website-grader

This document catalogs the entry points, codebase structure, and general current state of the website-grader repository prior to the Phase 0 foundation changes.

## 1. System Entry Points

The application provides two distinct operational entry points:

### A. Web Application (`app.py`)
- **Type:** Flask Micro-SaaS Web App.
- **Port:** Default is `5000` (or `PORT` environment variable).
- **Functionality:** 
  - Grades a target website based on a single page crawl/fetch.
  - Implements lightweight inline HTML templates and a standalone grading logic (`grade_website()`).
  - Collects user email leads and stores them in `emails.json`.
- **Routes:**
  - `GET /`: Renders the landing page with simple form.
  - `POST /grade`: Grades the URL from post data and returns rendered HTML report.
  - `POST /capture`: Captures customer emails for PDF follow-ups.
  - `GET/POST /api/grade`: JSON programmatic endpoint to grade target websites.
  - `GET /health`: JSON endpoint returning `{"status": "ok", "timestamp": ...}`.

### B. Command-Line Interface (`grader.py`)
- **Type:** CLI tool.
- **Functionality:**
  - Performs a deeper recursive crawl of up to `--max-pages` pages (default: 5) using `crawler.py`.
  - Runs all modular checkers registered in `checks/`.
  - Computes detailed scoring weights (`scoring.py`).
  - Generates recommended fixes and code suggestions (`fixes.py`).
  - Outputs reports as HTML (default: `report.html`) and/or JSON (using `-j/--json`).
- **Options:**
  - `url` (positional): Target URL to grade.
  - `--output` / `-o`: Destination path for the HTML report (default: `report.html`).
  - `--json` / `-j`: Destination path for the JSON audit report.
  - `--verbose` / `-v`: Verbose printing of status checks to standard output.
  - `--max-pages` / `-m`: Limit of pages to crawl (default: 5).

---

## 2. Directory and Codebase Structure

The repository has the following directory layout:

* **`checks/`**: Directory containing the checkers. Inherits base classes from `checks/base.py`.
  - `checks/__init__.py`: Lazy loader for category checker classes.
  - `checks/base.py`: Declares `CheckResult` dataclass, `Severity` enum, and `CheckCategory` base.
  - `checks/accessibility.py`: Accessibility validation rules.
  - `checks/content.py`: Core content audits.
  - `checks/conversion.py`: Click-to-action and social visibility rules.
  - `checks/local_seo.py`: Local NAP/GBP/Map rules.
  - `checks/performance.py`: Server and client performance checks.
  - `checks/security.py`: SSL, mixed-content, and security headers.
  - `checks/technical.py`: SEO technical tags, sitemaps, indexing, redirects, and broken links.
* **`app.py`**: Web-app interface and inline CSS/HTML templates.
* **`crawler.py`**: Web crawler that fetches HTML and response headers recursively, using `curl_cffi` to avoid bot protection.
* **`grader.py`**: CLI wrapper running the full crawl, check, scoring, and output pipeline.
* **`scoring.py`**: Category and severity weight scoring processor.
* **`fixes.py`**: Generates fix recommendation stubs.
* **`report.py`**: Compiles checking findings, scores, and fixes into a rich visual HTML report.
* **`tests/`**: Test suite directory.
  - `test_app.py`: Flask route and page tests.
  - `test_crawler.py`: Crawl extraction validation.
  - `test_scoring.py`: Test scoring weight calculation logic.
  - `test_technical.py`: Checks execution behaviors (e.g. heading structures).

---

## 3. Current Test Coverage

The test suite runs using `pytest` and contains 33 passing tests:
* `test_app.py`: 17 tests (client routing, error paths, email capture).
* `test_crawler.py`: 4 tests (crawling, priorities, links).
* `test_scoring.py`: 3 tests (category calculations, grades).
* `test_technical.py`: 9 tests (checks mapping, redirects, header validation).
