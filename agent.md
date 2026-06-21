# Developer & Subagent Integration Guide (AGENT.md)

This document is a technical, developer-focused reference guide. It outlines the codebase architecture, data schemas, routing, and conventions. It provides step-by-step instructions for autonomous subagents and developers to implement tasks, add new rules, and extend the engine without breaking compatibility.

---

## 1. Project Directory Structure

```
website-grader/
├── app.py                  # Flask web application (visualizer)
├── crawler.py               # Crawler using curl_cffi for Chrome impersonation
├── grader.py                # Command-line interface entry point
├── scoring.py               # Weighted scoring engine (health, coverage, etc.)
├── fixes.py                 # Fix templates and code generators
├── report.py                # Single-page HTML/PDF report builder
├── models.py                # Pydantic data schemas (AuditRun, Finding, etc.)
├── requirements.txt         # Package dependencies
├── PRD.md                   # Product Requirements Document
├── AGENT.md                 # This guide
├── checks/                  # Check modules package
│   ├── __init__.py          # Registry loader
│   ├── base.py              # Base CheckCategory, Severity, CheckResult
│   ├── technical.py         # Technical SEO checks
│   ├── performance.py       # Performance checks
│   ├── local_seo.py         # Local SEO checks
│   ├── content.py           # Content checks
│   ├── security.py          # Security checks
│   ├── accessibility.py     # Accessibility checks
│   └── conversion.py        # Conversion checks
└── tests/
    ├── test_app.py          # Flask routing & views tests
    ├── test_crawler.py      # Crawler test cases
    ├── test_scoring.py      # Score calculation tests
    └── test_technical.py    # Rule assertion and fixture tests
```

---

## 2. Core Architectural Pipeline

All diagnostic operations run through a sequential pipeline:

```
[Target URL] 
     ↓
1. Observability (crawler.py fetches homepage, sitemaps, robots.txt, CrUX)
     ↓
2. Normalization & Profiling (site type & page templates identified)
     ↓
3. Diagnosis (checks/ execute deterministic checks + link graph)
     ↓
4. Opportunities & Score (scoring.py computes Health, Coverage, Confidence)
     ↓
5. Presentation & Export (report.py generates report; fixes.py builds fixes)
```

---

## 3. Core Data Contracts (models.py)

We use versioned Pydantic schemas (implemented in `models.py`) to enforce type correctness and consistency across the engine.

### 3.1 Finding Status Enum
```python
from enum import Enum

class FindingStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNVERIFIED = "UNVERIFIED"
    ERROR = "ERROR"
    INFORMATIONAL = "INFORMATIONAL"
```

### 3.2 Evidence Model
Every finding that is a `FAIL` or `WARNING` **must** supply one or more immutable `Evidence` objects.
```python
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

class Evidence(BaseModel):
    evidence_id: str
    type: str               # e.g., "selector", "http_trace", "content_excerpt"
    page_url: str
    observed_value: Any     # Dict, string, array, or numeric value observed
    selector: Optional[str] = None  # CSS selector if applicable
    captured_at: datetime   # Configured via Field(default_factory=...)
```

### 3.3 Finding Model
```python
from pydantic import BaseModel
from typing import List, Optional

class Finding(BaseModel):
    finding_id: str
    check_id: str
    category: str
    status: FindingStatus
    severity: str           # "critical", "high", "medium", "low", "info"
    scope: str              # "page" or "site"
    page_url: Optional[str] = None
    title: str
    observation: str
    applicable: bool
    confidence: float       # 0.0 to 1.0
    evidence: List[Evidence] = []
    recommendation_id: Optional[str] = None
```

---

## 4. How to Implement a New Check

When implementing a task to add a new check, follow this step-by-step protocol.

### Step 1: Define check metadata and applicability
All checks must reside inside subclasses of `CheckCategory` in `checks/`. Define the check inside the appropriate file (e.g., `checks/technical.py` or `checks/agentic.py`).

Ensure the check defines:
1. **Applicability:** Which site types and page types does this rule target?
2. **Deterministic Facts:** The check must extract values and build an `Evidence` trail. Never make up details or rely on raw heuristics when facts can be verified.

```python
def _check_llms_txt(self, crawl_result) -> CheckResult:
    # 1. Fetch robots or check root content
    # 2. Extract facts and create evidence
    # 3. Determine status based on facts
```

### Step 2: Return a standard CheckResult with Evidence
Update your check method to return a standard `CheckResult` populated with `Evidence` objects. Note that optional files (like `llms.txt`) must be reported as `INFORMATIONAL`, not a `FAIL`, and must not lower the score.

```python
from checks.base import CheckResult, Severity
from models import FindingStatus, Evidence
import uuid

# Example check logic for an optional file (llms.txt)
passed = True
status = FindingStatus.INFORMATIONAL
evidence_list = []
detail = "Valid optional llms.txt found at root"

if not llms_txt_found:
    evidence_list.append(
        Evidence(
            evidence_id=str(uuid.uuid4()),
            type="http_status",
            page_url=f"{crawl_result.base_url}/llms.txt",
            observed_value={"status_code": 404}
        )
    )
    detail = "Optional llms.txt not found at root"

return CheckResult(
    check_id="agentic_llms_txt",
    check_name="LLMs Sitemap (llms.txt)",
    category=self.category_name,
    severity=Severity.INFO,
    passed=passed,
    status=status,
    score=100,  # Informational checks do not penalize scoring
    detail=detail,
    evidence=evidence_list,
    recommendation="Optional experimental file. Only implement if part of an explicit AI-content-access strategy.",
    fix_difficulty="Easy (5 min)",
    impact_estimate="Info",
    data={"applicability": "optional"}
)
```
*(Do not claim that `llms.txt` improves Google rankings, ChatGPT visibility, Perplexity citations, or AI model parsing unless a provider-specific documented source is later connected to a supported-feature registry.)*

### Step 3: Register the Check
Ensure your check method is registered in the category's `run()` loop:
```python
def run(self, crawl_result) -> List[CheckResult]:
    results = []
    # ... other checks ...
    results.append(self._check_llms_txt(crawl_result))
    return results
```

### Step 4: Write Unit Tests
Open the corresponding test file under `tests/` (e.g. `test_technical.py`) and write test cases targeting the new check with mock HTML payloads and response structures.

```python
def test_llms_txt_missing():
    crawl_result = MockCrawlResult(base_url="https://example.com", pages={})
    # Mock /llms.txt returning 404
    checker = TechnicalChecks()
    result = checker._check_llms_txt(crawl_result)
    assert result.status == FindingStatus.INFORMATIONAL
    assert result.severity == Severity.INFO
    assert len(result.evidence) == 1
    assert result.evidence[0].observed_value["status_code"] == 404
```

### Step 5: Verify the Test Suite
Always run `pytest` to make sure your checks work and no regressions are introduced.

```bash
pytest tests/test_technical.py
```

---

## 5. Ponytail (Lazy Senior Dev) Integration Rules

When you write code, you must follow these rules without exception:

1. **YAGNI (You Aren't Gonna Need It):** Do not add speculative code, options, or hooks that are not requested by the current task backlog.
2. **Minimal Dependencies:** Never introduce third-party libraries (e.g., NumPy, Pandas, custom date parsers) if the standard library can do it. Stick strictly to standard packages and existing libraries (`requests`, `beautifulsoup4`, `curl_cffi`, `flask`, `pydantic`).
3. **One Line Over Ten:** If a string manipulation, JSON check, or regex match can be written on a single clean line, write it in one line. Do not write a 15-line helper class for it.
4. **Preserve Truth:** Never use AI/LLMs to override response codes, DOM tags, titles, or SSL details. AI must only interpret facts, never fabricate them.
5. **No Placeholders:** If a recommendation has a fix code block, it must be a valid code template. Never generate dummy addresses, phone numbers, or ratings.
6. **Strict Truth Layer:** Ponytail mode must never be used as an excuse to skip evidence, tests, data contracts, compatibility, or release gates. Keep the code simple, but keep the truth layer strict.

---

## 6. Strict Scope Control & Scope Creep Prevention

The coding agent working on the codebase may **only** execute tasks **WG-001 through WG-006** (Phase 0: Foundation). It is strictly forbidden from implementing:
* New SEO checks
* New scoring formulas
* Playwright rendering engines
* Lighthouse lab tests
* axe-core integration
* Google Search Console or Google Analytics 4 adapters
* AI search/GEO visibility checks
* Local SEO category rewrites
* Report UI redesigns
* Multi-tenant or billing modules

*The coding agent is building the foundation, not the cathedral. Humans already tried tower-building once and it produced JavaScript frameworks.*
