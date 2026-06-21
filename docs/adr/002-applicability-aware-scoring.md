# ADR 002: Applicability-Aware Scoring Framework

* **Status:** Accepted
* **Date:** 2026-06-21
* **Author:** Antigravity (Ponytail Coder)

## Context
Our current scoring formula (`scoring.py`) calculates a single overall score. Any failed check directly penalizes the website's grade. This causes critical issues for non-local sites (e.g., SaaS platforms or ecommerce sites) which are penalized with 0/100 on the Local SEO category because they do not have a physical map embed or a physical address. 
Additionally, system limitations (like missing API credentials to check Google Search Console) are lumped into the general scoring, making the site look unhealthy when it's simply a coverage gap.

## Decision
We will transition to a **Four-Pillar Scoring Model**:
1. **Website Health:** The core quality score computed *exclusively* from evaluated, **applicable** checks. Non-applicable checks (like Local SEO checks on national SaaS sites) are omitted entirely from both the numerator and denominator.
2. **Audit Coverage:** Measures the percentage of the platform's capability that was executed. Unconfigured API integrations (e.g. GSC/GA4) reduce this score rather than health.
3. **Evidence Confidence:** Indicates the certainty of findings, separating deterministic checks (e.g., 404 links) from heuristic or AI classification checks.
4. **Opportunity Potential:** Estimates business upside of implementing fixes based on query volume, feasibility, and conversion intent.

## Consequences
* **Positive:** Scores are accurate and customized to site profiles (SaaS vs Local Business).
* **Positive:** Clear separation between website errors (Health) and grader configuration gaps (Coverage).
* **Negative:** Requires a classification step (Site Profile) before scoring runs.
