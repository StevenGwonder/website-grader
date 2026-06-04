import unittest
from checks.base import CheckResult, Severity
from scoring import compute_score, score_to_grade

class TestScoring(unittest.TestCase):
    def test_perfect_score(self):
        results = [
            CheckResult(
                check_id=f"check_{i}",
                check_name=f"Test Check {i}",
                category="Technical SEO",
                severity=Severity.HIGH,
                passed=True,
                score=100,
                detail="",
                recommendation=""
            )
            for i in range(5)
        ]
        score = compute_score(results)
        self.assertEqual(score["overall_score"], 100)
        self.assertEqual(score["grade"], "A")

    def test_all_fail(self):
        results = [
            CheckResult(
                check_id=f"check_{i}",
                check_name=f"Test Check {i}",
                category="Technical SEO",
                severity=Severity.HIGH,
                passed=False,
                score=0,
                detail="",
                recommendation=""
            )
            for i in range(5)
        ]
        score = compute_score(results)
        self.assertEqual(score["overall_score"], 0)
        self.assertEqual(score["grade"], "F")

    def test_mixed_results(self):
        results = [
            CheckResult(
                check_id=f"check_{i}",
                check_name=f"Test Check {i}",
                category="Technical SEO",
                severity=Severity.HIGH,
                passed=(i % 2 == 0),
                score=100 if i % 2 == 0 else 0,
                detail="",
                recommendation=""
            )
            for i in range(10)
        ]
        score = compute_score(results)
        self.assertTrue(40 <= score["overall_score"] <= 60)
        self.assertIn(score["grade"], ["D", "F"])

if __name__ == "__main__":
    unittest.main()
