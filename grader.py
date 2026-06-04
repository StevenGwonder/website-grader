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

    score_data = compute_score(all_results)
    print(f"  Score: {score_data['overall_score']}/100 (Grade {score_data['grade']})")

    fixes = generate_fixes(crawl_result, all_results)

    try:
        from report import generate_report
        html = generate_report(crawl_result, all_results, score_data, fixes, args.url)
        with open(args.output, "w") as f:
            f.write(html)
        print(f"  Report: {args.output}")
    except ImportError:
        print("  (report.py not yet available — skipping HTML report)")

    if args.json:
        report_data = {
            "url": args.url,
            "score": score_data,
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
