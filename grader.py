#!/usr/bin/env python3
"""CLI mode for website grader — python3 grader.py <url>"""
import sys
import os
from datetime import datetime
from crawler import crawl_site
from checks import _load_categories
from scoring import compute_score
from fixes import generate_fixes
from report import generate_report


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 grader.py <url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("http"):
        url = "https://" + url

    try:
        crawl_result = crawl_site(url, max_pages=3)
        if crawl_result.error and not crawl_result.pages:
            print(f"Error: Could not reach {url} — {crawl_result.error}", file=sys.stderr)
            sys.exit(1)

        all_results = []
        for CheckClass in _load_categories():
            checker = CheckClass()
            results = checker.run(crawl_result)
            all_results.extend(results)

        score_data = compute_score(all_results, crawl_result)
        fixes = generate_fixes(crawl_result, all_results)
        html = generate_report(crawl_result, all_results, score_data, fixes, url)

        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        timestamp = datetime.now().strftime("%Y-%m-%d")
        os.makedirs("reports", exist_ok=True)
        filename = f"reports/{domain}-{timestamp}.html"
        with open(filename, "w") as f:
            f.write(html)
        print(f"Report saved to {filename}")

    except Exception as e:
        print(f"Error grading {url}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
