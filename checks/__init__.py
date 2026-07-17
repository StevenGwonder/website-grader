from functools import lru_cache
from checks.base import CheckCategory, Severity, CheckResult


@lru_cache(maxsize=None)
def _load_categories():
    from checks.technical import TechnicalChecks
    from checks.performance import PerformanceChecks
    from checks.local_seo import LocalSeoChecks
    from checks.content import ContentChecks
    from checks.security import SecurityChecks
    from checks.accessibility import AccessibilityChecks
    from checks.conversion import ConversionChecks
    from checks.external_intelligence import ExternalIntelligenceChecks
    return [
        TechnicalChecks,
        PerformanceChecks,
        LocalSeoChecks,
        ContentChecks,
        SecurityChecks,
        AccessibilityChecks,
        ConversionChecks,
        ExternalIntelligenceChecks,
    ]
