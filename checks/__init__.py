from checks.base import CheckCategory, Severity, CheckResult

# Check categories are imported lazily to avoid circular imports
# until all modules are implemented
ALL_CHECK_CATEGORIES = []

def _load_categories():
    global ALL_CHECK_CATEGORIES
    if ALL_CHECK_CATEGORIES:
        return ALL_CHECK_CATEGORIES
    from checks.technical import TechnicalChecks
    from checks.performance import PerformanceChecks
    from checks.local_seo import LocalSeoChecks
    from checks.content import ContentChecks
    from checks.security import SecurityChecks
    from checks.accessibility import AccessibilityChecks
    from checks.conversion import ConversionChecks
    ALL_CHECK_CATEGORIES = [
        TechnicalChecks,
        PerformanceChecks,
        LocalSeoChecks,
        ContentChecks,
        SecurityChecks,
        AccessibilityChecks,
        ConversionChecks,
    ]
    return ALL_CHECK_CATEGORIES
