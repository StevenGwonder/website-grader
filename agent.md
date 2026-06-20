# Developer & Subagent Integration Guide (AGENT.md)

This document is a technical developer-focused reference guide. It outlines the codebase architecture, file structures, routing mechanisms, and conventions. It provides step-by-step instructions for autonomous agents (or developers) to run tests, write new tests, create new check categories, implement checklist tasks, and integrate new metrics without breaking backward compatibility.

---

## 1. Project Directory Structure

```
website-grader/
├── app.py                  # Flask web application & templates
├── crawler.py               # Web crawler using curl_cffi for Chrome impersonation
├── grader.py                # Command-line interface entry point
├── scoring.py               # Weighted scoring engine
├── fixes.py                 # Fix generator producing copy-pasteable HTML/JSON
├── report.py                # HTML report builder (Jinja-free string mapping)
├── requirements.txt         # Package dependencies (flask, requests, bs4, curl_cffi)
├── README.md                # General introduction & quick start guide
├── PRD.md                   # Product Requirements Document & phased roadmap
├── agent.md                 # This developer & subagent integration guide
├── checks/                  # Check modules package
│   ├── __init__.py          # Category lazy-loader registry
│   ├── base.py              # Base CheckCategory, Severity, CheckResult dataclasses
│   ├── technical.py         # Technical SEO checks (title, desc, canonical, etc.)
│   ├── performance.py       # Performance checks (ttfb, weight, images, cache, etc.)
│   ├── local_seo.py         # Local SEO NAP extraction & schema audits
│   ├── content.py           # Word count, readability, keyword density checks
│   ├── security.py          # SSL check, security headers, mixed content
│   ├── accessibility.py     # Heading levels, form labels, alt tags
│   └── conversion.py        # Social links, analytics tracking, forms
└── tests/ (or root tests)
    ├── test_app.py          # Flask routing & endpoint tests
    ├── test_crawler.py      # Crawler test cases (priority crawling, internal links)
    ├── test_scoring.py      # Scoring calculations and grade bounds tests
    └── test_technical.py    # Mock check assertions (runs checks against HTML)
```

---

## 2. Core Architectural Components

### 2.1 Web Crawling Pipeline
The file [crawler.py](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/crawler.py) fetches and processes HTML data. 
* **`PageData` (Dataclass):** Represents a single crawled URL. Stores raw HTML, final redirects URL, HTTP status code, Time to First Byte (`ttfb_ms`), headers dict, and parsed BeautifulSoup object.
* **`CrawlResult` (Dataclass):** Stores the crawling session context. Maps page URLs to their corresponding `PageData` objects. Holds root files like `robots.txt` and `sitemap.xml`.
* **`crawl_site(url, max_pages, timeout)`:** Crawls the website. First downloads the homepage, `robots.txt`, and `sitemap.xml`. Then, extracts internal links, prioritizes key pages (e.g. contact, about, services), and crawls up to `max_pages` using a `curl_cffi` request session impersonating Google Chrome.

### 2.2 Checks Architecture
Checks are implemented inside the [checks/](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/checks) directory.
* **`Severity` (Enum):** Classifies failures: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`.
* **`CheckResult` (Dataclass):** Standard output for every check. Defined in [base.py](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/checks/base.py), it includes:
  ```python
  check_id: str          # Unique key (e.g., 'performance_ttfb')
  check_name: str        # Label for displays
  category: str          # Name of the category
  severity: Severity     # Enum severity
  passed: bool           # True if passes benchmarks
  score: int             # 0-100 check score
  detail: str            # Technical message
  recommendation: str    # Compelling instruction on how to fix it
  fix_code: str          # Copy-pasteable HTML/JS snippet
  fix_difficulty: str    # "Easy (1 min)", "Medium (30 min)", etc.
  impact_estimate: str   # "Critical", "High", "Medium", "Low"
  data: dict             # Raw dictionary data for reporting
  ```
* **`CheckCategory` (Base Class):** Interface that all categories subclass. Implements `run(self, crawl_result) -> List[CheckResult]`.
* **Registry Loader:** [__init__.py](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/checks/__init__.py) lazy-loads check classes in `_load_categories()` to prevent circular imports.

### 2.3 Scoring Engine
The file [scoring.py](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/scoring.py) computes overall values.
* **Category Weights:** Maps categories to percentage weights (e.g., Technical SEO 25%, Local SEO 20%).
* **Severity Scaling:** Scales scoring dynamically based on check severity (`CRITICAL` = 4x, `HIGH` = 3x, etc.) so that failing critical checks impacts the score more heavily than failing low-priority checks.
* **`compute_score(results)`:** Compiles raw check outputs, weighs category scores, and assigns a letter grade (`A` to `F`).

### 2.4 User Interfaces & CLI
* **Web Server:** [app.py](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/app.py) is a self-contained Flask app running on port 5000. It handles standard pages, grade queries (`/grade` and `/api/grade`), and email submissions (`/capture`).
* **Command Line Interface:** [grader.py](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/grader.py) allows developers to run audits from the terminal. Example:
  ```bash
  python3 grader.py https://example.com --output report.html --verbose
  ```

---

## 3. How to Run & Verify the Codebase

### 3.1 Setup & Dependencies
Dependencies are listed in [requirements.txt](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/requirements.txt).
To install them (in environments where system packages are externally managed, append the user-override flag):
```bash
pip install -r requirements.txt --break-system-packages
```

### 3.2 Running the Application
* **CLI Execution:**
  ```bash
  python3 grader.py https://example.com
  ```
* **Web Server Execution:**
  ```bash
  python3 app.py
  ```
  Once launched, open your browser and navigate to `http://localhost:5000`.

### 3.3 Running Unit Tests
We use `pytest` for the testing suite. To execute the tests, run:
```bash
# Run all tests
pytest

# Run tests containing a specific keyword (e.g., crawler)
pytest -k crawler

# Run tests in verbose mode showing execution timings
pytest -v
```

---

## 4. Instructions for Autonomous Agents (Writing New Checks)

When a subagent receives a task to implement a new check (from any phase of the [PRD.md](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/PRD.md)), follow this protocol:

### Step 1: Create or Update the Check Class
Write your diagnostic method inside the relevant file in [checks/](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/checks). 

> [!NOTE]
> Ensure the method prefix is `_check_` so it is easily identified by the class runner.

Example: Adding a check for `llms.txt` in a file:
```python
def _check_llms_txt(self, crawl_result) -> CheckResult:
    # 1. Fetch robots or check root content
    # 2. Benchmark the results
    passed = False
    detail = "No llms.txt found at root"
    
    # 3. Return the standard CheckResult
    return CheckResult(
        check_id="agentic_llms_txt",
        check_name="LLMs Sitemap (llms.txt)",
        category=self.category_name,
        severity=Severity.MEDIUM,
        passed=passed,
        score=0 if not passed else 100,
        detail=detail,
        recommendation="Create an /llms.txt file at your root directory to help LLMs read your site structure.",
        fix_code="See https://llmstxt.org/ for syntax guidelines.",
        fix_difficulty="Easy (5 min)",
        impact_estimate="Medium"
    )
```

### Step 2: Append check method to category runtime list
Ensure that your check method is called in the category's `run()` method.
```diff
     def run(self, crawl_result) -> List[CheckResult]:
         results = []
         results.append(self._check_meta_title(homepage))
+        results.append(self._check_llms_txt(crawl_result))
         return results
```

### Step 3: Write a Unit Test
Open [test_technical.py](file:///home/stevengwonder/.openclaw/workspace/repos/website-grader/test_technical.py) (or the corresponding test file for the category) and add a test case. Mock HTML payloads or HTTP responses to verify both pass and fail criteria.
```python
def test_llms_txt_check_missing():
    # Setup mock CrawlResult with no root file
    crawl_result = MockCrawlResult(robots_txt="", sitemap_xml="", pages={})
    checker = TechnicalChecks()
    result = checker._check_llms_txt(crawl_result)
    assert result.passed is False
    assert result.score == 0
```

### Step 4: Run validation tests
Execute `pytest` to verify the new check works correctly and does not break existing metrics. Ensure that code edits maintain clean syntax, correct imports, and proper exception handling.
