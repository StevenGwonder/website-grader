from typing import List, Dict, Any
from checks.base import CheckResult, Severity

CATEGORY_WEIGHTS = {
    "Technical SEO": 25,
    "Local SEO": 20,
    "Performance": 15,
    "Content Quality": 15,
    "Security": 10,
    "Accessibility": 10,
    "Social & Conversion": 5
}

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 4,
    Severity.HIGH: 3,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
    Severity.INFO: 0.5
}

def compute_score(results: List[CheckResult]) -> Dict[str, Any]:
    categories = {}
    for cat, weight in CATEGORY_WEIGHTS.items():
        cat_results = [r for r in results if r.category == cat]
        if not cat_results:
            continue

        total_weighted = 0
        total_possible = 0
        passed = 0

        for r in cat_results:
            severity_weight = SEVERITY_WEIGHTS[r.severity]
            total_weighted += r.score * severity_weight
            total_possible += 100 * severity_weight
            if r.passed:
                passed += 1

        if total_possible == 0:
            cat_score = 0
        else:
            cat_score = (total_weighted / total_possible) * 100

        categories[cat] = {
            "score": int(cat_score),
            "weight": weight,
            "checks_passed": passed,
            "checks_total": len(cat_results)
        }

    active_weight = sum(data["weight"] for data in categories.values())
    if active_weight == 0:
        overall = 0
    else:
        overall = sum(
            (data["score"] * data["weight"]) / active_weight
            for data in categories.values()
        )
    grade = score_to_grade(overall)

    return {
        "overall_score": int(overall),
        "grade": grade,
        "categories": categories
    }

def score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"

def deduplicate_findings(findings: list) -> list:
    from models import FindingStatus
    grouped = {}
    for f in findings:
        if f.status in (FindingStatus.PASS, FindingStatus.INFORMATIONAL, FindingStatus.NOT_APPLICABLE):
            key = (f.check_id, id(f))
        else:
            selector = None
            if f.evidence:
                selector = f.evidence[0].selector
            key = (f.check_id, f.observation, selector)
            
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(f)
        
    deduplicated = []
    for key, items in grouped.items():
        if len(items) == 1:
            deduplicated.append(items[0])
        else:
            base = items[0]
            combined_evidence = []
            seen_evidence = set()
            for item in items:
                for ev in item.evidence:
                    ev_key = (ev.page_url, ev.selector, str(ev.observed_value))
                    if ev_key not in seen_evidence:
                        seen_evidence.add(ev_key)
                        combined_evidence.append(ev)
            base.evidence = combined_evidence
            base.scope = "site"
            base.observation = f"{base.observation} (Found on {len(items)} pages)"
            deduplicated.append(base)
            
    return deduplicated

