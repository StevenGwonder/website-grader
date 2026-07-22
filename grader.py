import argparse, json, sys
from crawler import crawl_site
from checks import _load_categories
from scoring import compute_score
from fixes import generate_fixes

def main():
    parser = argparse.ArgumentParser(description="Website Grader Pro")
    parser.add_argument("url", help="URL to grade")
    parser.add_argument("--output", "-o", default="report.html", help="HTML output path")
    parser.add_argument("--json", "-j", help="JSON output path")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--max-pages", "-m", type=int, default=5)
    args = parser.parse_args()

    print(f"Grading {args.url}...")

    print(f"  Crawling (up to {args.max_pages} pages)...")
    crawl_result = crawl_site(args.url, max_pages=args.max_pages)
    if crawl_result.error:
        print(f"  Error: {crawl_result.error}")
        sys.exit(1)
    print(f"  Crawled {len(crawl_result.pages)} pages")

    all_results = []
    for CheckClass in _load_categories():
        checker = CheckClass()
        results = checker.run(crawl_result)
        all_results.extend(results)
        passed = sum(1 for r in results if r.passed)
        print(f"  {checker.category_name}: {passed}/{len(results)} passed")

    score_data = compute_score(all_results, crawl_result)
    print(f"  Score: {score_data['overall_score']}/100 (Grade {score_data['grade']})")
    print(f"    Health Score: {score_data.get('health_score', 0.0)}")
    print(f"    Coverage Score: {score_data.get('coverage_score', 0.0)}")
    print(f"    Confidence Score: {score_data.get('confidence_score', 0.0)}")
    print(f"    Improvement Potential: {score_data.get('improvement_potential', 0.0)}")
    if score_data.get('site_blocked'):
        print(f"    ⚠️  Site was blocked by bot protection — grade reflects limited data")
    elif score_data.get('blocked_pages', 0) > 0:
        print(f"    ⚠️  {score_data['blocked_pages']}/{score_data['total_pages']} pages blocked by bot protection")


    # Print crawl audit coverage metadata
    print("\n  Audit Coverage Metadata:")
    print(f"    Discovered URLs: {len(crawl_result.discovered_urls)}")
    print(f"    Crawled URLs: {len(crawl_result.crawled_urls)}")
    print(f"    Excluded URLs: {len(crawl_result.excluded_urls)}")
    print(f"    Fetch failures: {len(crawl_result.fetch_failures)}")
    print(f"    Evaluated checks: {len(all_results)} (0 unavailable)")

    fixes = generate_fixes(crawl_result, all_results)

    from report import generate_report
    html = generate_report(crawl_result, all_results, score_data, fixes, args.url)
    with open(args.output, "w") as f:
        f.write(html)
    print(f"  Report: {args.output}")

    if args.json:
        report_data = {
            "url": args.url,
            "score": score_data,
            "metadata": {
                "discovered_urls": list(crawl_result.discovered_urls),
                "crawled_urls": list(crawl_result.crawled_urls),
                "excluded_urls": list(crawl_result.excluded_urls),
                "fetch_failures": crawl_result.fetch_failures,
                "external_integrations": {
                    "google_search_console": "unavailable",
                    "google_analytics_4": "unavailable",
                    "crux": "unavailable"
                },
                "evaluated_checks_count": len(all_results),
                "unavailable_checks_count": 0
            },
            "checks": [{"check_id": r.check_id, "name": r.check_name, "category": r.category,
                        "severity": r.severity.value, "passed": r.passed, "score": r.score,
                        "detail": r.detail, "recommendation": r.recommendation}
                       for r in all_results],
        }
        with open(args.json, "w") as f:
            json.dump(report_data, f, indent=2)
        print(f"  JSON: {args.json}")

    if args.verbose:
        print()
        for r in all_results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{r.severity.value:8s}] {status} {r.check_name}: {r.detail[:60]}")

if __name__ == "__main__":
    main()
