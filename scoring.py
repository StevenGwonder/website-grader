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
