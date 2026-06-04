import re
from bs4 import BeautifulSoup
from .base import CheckResult, Severity, CheckCategory

class AccessibilityChecks(CheckCategory):
    category_name = "Accessibility"
    category_weight = 10

    def run(self, crawl_result):
        page = crawl_result.homepage
        if not page or not page.soup:
            return []

        results = []
        results.append(self._check_alt_text(page))
        results.append(self._check_form_labels(page))
        results.append(self._check_heading_order(page))
        results.append(self._check_aria_labels(page))
        results.append(self._check_skip_nav(page))
        return results

    def _check_alt_text(self, page):
        soup = page.soup
        images = soup.find_all('img')
        total = len(images)
        if total == 0:
            return CheckResult(
                check_id="alt_text",
                check_name="Image Alt Text",
                category=self.category_name,
                severity=Severity.HIGH,
                passed=True,
                score=100,
                detail="No images found",
                recommendation="Add alt text to images for accessibility",
            )

        with_alt = sum(1 for img in images if img.get('alt', '').strip())
        score = (with_alt / total) * 100
        passed = score == 100
        detail = f"{with_alt} of {total} images have alt text"

        return CheckResult(
            check_id="alt_text",
            check_name="Image Alt Text",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=int(score),
            detail=detail,
            recommendation="Add descriptive alt text to all images",
        )

    def _check_form_labels(self, page):
        soup = page.soup
        inputs = soup.find_all('input', type=lambda x: x != 'hidden' if x else True)
        total = len(inputs)
        if total == 0:
            return CheckResult(
                check_id="form_labels",
                check_name="Form Labels",
                category=self.category_name,
                severity=Severity.MEDIUM,
                passed=True,
                score=100,
                detail="No form inputs found",
                recommendation="Ensure all form inputs have labels",
            )

        labeled = 0
        for inp in inputs:
            inp_id = inp.get('id')
            if inp_id and soup.find('label', attrs={'for': inp_id}):
                labeled += 1
            elif inp.find_parent('label'):
                labeled += 1
            elif inp.get('aria-label'):
                labeled += 1

        score = (labeled / total) * 100
        passed = score >= 80
        detail = f"{labeled} of {total} inputs have labels"

        return CheckResult(
            check_id="form_labels",
            check_name="Form Labels",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=int(score),
            detail=detail,
            recommendation="Add labels to all form inputs using <label> or aria-label",
        )

    def _check_heading_order(self, page):
        soup = page.soup
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if not headings:
            return CheckResult(
                check_id="heading_order",
                check_name="Heading Order",
                category=self.category_name,
                severity=Severity.MEDIUM,
                passed=True,
                score=100,
                detail="No headings found",
                recommendation="Use proper heading hierarchy (h1 to h6)",
            )

        levels = [int(h.name[1:]) for h in headings]
        passed = True
        detail = "Heading order: " + ", ".join(h.name for h in headings)

        for i in range(1, len(levels)):
            if levels[i] > levels[i-1] + 1:
                passed = False
                detail = f"Skipped from h{levels[i-1]} to h{levels[i]}"
                break

        return CheckResult(
            check_id="heading_order",
            check_name="Heading Order",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=100 if passed else 0,
            detail=detail,
            recommendation="Maintain proper heading hierarchy without skipping levels",
        )

    def _check_aria_labels(self, page):
        soup = page.soup
        interactive = soup.find_all(['button', 'a', 'input'])
        missing = 0
        for elem in interactive:
            if elem.get('role') and not elem.get('aria-label'):
                missing += 1

        passed = missing == 0
        detail = f"{missing} interactive elements missing aria-label"

        return CheckResult(
            check_id="aria_labels",
            check_name="ARIA Labels",
            category=self.category_name,
            severity=Severity.LOW,
            passed=passed,
            score=100 if passed else 0,
            detail=detail,
            recommendation="Add aria-label to interactive elements with roles",
        )

    def _check_skip_nav(self, page):
        soup = page.soup
        skip_links = soup.find_all('a', href=lambda x: x in ['#main', '#content'] if x else False)
        skip_links += soup.find_all('a', class_=lambda x: x and 'skip' in x.split())

        passed = len(skip_links) > 0
        detail = "Skip navigation link found" if passed else "No skip navigation link found"

        return CheckResult(
            check_id="skip_nav",
            check_name="Skip Navigation",
            category=self.category_name,
            severity=Severity.LOW,
            passed=passed,
            score=100 if passed else 0,
            detail=detail,
            recommendation="Add a skip navigation link for keyboard users",
        )
