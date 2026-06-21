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

def compute_score(results: List[CheckResult], crawl_result: Any = None) -> Dict[str, Any]:
    from models import FindingStatus
    
    categories = {}
    for cat, weight in CATEGORY_WEIGHTS.items():
        cat_results = [r for r in results if r.category == cat]
        if not cat_results:
            continue

        cat_applicable = [r for r in cat_results if r.status not in (FindingStatus.NOT_APPLICABLE, FindingStatus.INFORMATIONAL, FindingStatus.ERROR)]
        
        passed = sum(1 for r in cat_results if r.passed)
        
        if not cat_applicable:
            cat_score = 100.0
        else:
            total_weighted = sum(r.score * SEVERITY_WEIGHTS[r.severity] for r in cat_applicable)
            total_possible = sum(100 * SEVERITY_WEIGHTS[r.severity] for r in cat_applicable)
            cat_score = (total_weighted / total_possible) * 100 if total_possible > 0 else 100.0

        categories[cat] = {
            "score": int(cat_score),
            "weight": weight,
            "checks_passed": passed,
            "checks_total": len(cat_results),
            "applicable_count": len(cat_applicable)
        }

    active_cats = {cat: data for cat, data in categories.items() if data["applicable_count"] > 0}
    if not active_cats:
        overall_health = 100.0
    else:
        overall_health = sum(data["score"] * data["weight"] for data in active_cats.values()) / sum(data["weight"] for data in active_cats.values())

    from checks.registry import RULE_REGISTRY
    total_applicable_weight = 0
    evaluated_applicable_weight = 0
    
    site_type = "other"
    if crawl_result:
        site_type = getattr(crawl_result, "site_type", "other")
        
    evaluated_ids = {r.check_id for r in results}
    
    for check_id, meta in RULE_REGISTRY.items():
        site_app = meta.applicability.get("site_types", ["*"])
        site_applicable = False
        for t in site_app:
            if t == "*" or t == site_type or (t == "local" and site_type in ("local_service_business", "local_storefront", "multi_location_business")):
                site_applicable = True
                
        if site_applicable:
            total_applicable_weight += meta.default_weight
            if check_id in evaluated_ids:
                evaluated_applicable_weight += meta.default_weight
                
    if total_applicable_weight > 0:
        check_coverage = (evaluated_applicable_weight / total_applicable_weight) * 100
    else:
        check_coverage = 100.0
        
    coverage_score = check_coverage
    if crawl_result:
        integrations = {
            "google_search_console": "unavailable",
            "google_analytics_4": "unavailable",
            "crux": "unavailable"
        }
        if hasattr(crawl_result, "external_integrations"):
            integrations = crawl_result.external_integrations
        elif hasattr(crawl_result, "metadata") and "external_integrations" in crawl_result.metadata:
            integrations = crawl_result.metadata["external_integrations"]
            
        for status in integrations.values():
            if status == "unavailable":
                coverage_score -= 10.0
            
    coverage_score = max(0.0, min(100.0, coverage_score))


    confidence_score = 100.0
    disparity_count = 0
    if crawl_result and hasattr(crawl_result, "pages"):
        for page in crawl_result.pages.values():
            if getattr(page, "raw_vs_rendered_disparities", None):
                disparity_count += 1
        if disparity_count > 0:
            confidence_score -= min(15.0, disparity_count * 5.0)
            
    unsupported_failures = 0
    for r in results:
        if r.status not in (FindingStatus.NOT_APPLICABLE, FindingStatus.INFORMATIONAL, FindingStatus.ERROR):
            if r.status in (FindingStatus.FAIL, FindingStatus.WARNING):
                if not getattr(r, "evidence", None):
                    unsupported_failures += 1
    if unsupported_failures > 0:
        confidence_score -= min(15.0, unsupported_failures * 3.0)
        
    if crawl_result and not getattr(crawl_result, "overrides", None):
        confidence_score -= 5.0
        
    confidence_score = max(0.0, min(100.0, confidence_score))

    total_opt = 0
    max_opt = 0
    for r in results:
        if r.status not in (FindingStatus.NOT_APPLICABLE, FindingStatus.INFORMATIONAL, FindingStatus.ERROR):
            sev_w = SEVERITY_WEIGHTS.get(r.severity, 1.0)
            ease_str = getattr(r, "fix_difficulty", "Easy") or "Easy"
            if "easy" in ease_str.lower():
                ease_w = 3.0
            elif "medium" in ease_str.lower():
                ease_w = 2.0
            else:
                ease_w = 1.0
                
            check_max = sev_w * ease_w
            max_opt += check_max
            if r.status in (FindingStatus.FAIL, FindingStatus.WARNING):
                total_opt += check_max
                
    opportunity_score = (total_opt / max_opt) * 100.0 if max_opt > 0 else 0.0

    grade = score_to_grade(overall_health)

    return {
        "overall_score": int(overall_health),
        "health_score": round(overall_health, 1),
        "coverage_score": round(coverage_score, 1),
        "confidence_score": round(confidence_score, 1),
        "opportunity_score": round(opportunity_score, 1),
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

