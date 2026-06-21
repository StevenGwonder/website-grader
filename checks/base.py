from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from models import FindingStatus, Evidence

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class CheckResult:
    check_id: str
    check_name: str
    category: str
    severity: Severity
    passed: bool
    score: int
    detail: str
    recommendation: str = ""
    fix_code: Optional[str] = None
    fix_difficulty: str = ""
    impact_estimate: str = ""
    data: dict = field(default_factory=dict)
    status: Optional[FindingStatus] = None
    evidence: List[Evidence] = field(default_factory=list)
    page_url: Optional[str] = None

    def __post_init__(self):
        from checks.registry import get_rule_metadata
        meta = get_rule_metadata(self.check_id)
        if meta:
            self.check_name = meta.name
            self.category = meta.category
            if not self.recommendation:
                self.recommendation = meta.recommendation_template

        if self.status is None:
            if self.passed:
                if self.severity == Severity.INFO or (meta and meta.default_severity == "info"):
                    self.status = FindingStatus.INFORMATIONAL
                else:
                    self.status = FindingStatus.PASS
            else:
                if self.severity == Severity.INFO or (meta and meta.default_severity == "info"):
                    self.status = FindingStatus.INFORMATIONAL
                elif self.score > 0 and self.score < 100:
                    self.status = FindingStatus.WARNING
                else:
                    self.status = FindingStatus.FAIL
        else:
            self.passed = self.status in (FindingStatus.PASS, FindingStatus.INFORMATIONAL, FindingStatus.NOT_APPLICABLE, FindingStatus.UNVERIFIED)

        # WG-009: Implement evidence persistence
        if self.status in (FindingStatus.FAIL, FindingStatus.WARNING) and not self.evidence:
            import uuid
            from datetime import datetime, timezone
            from models import Evidence as ModelEvidence

            url = self.page_url or "https://example.com"
            selector = None
            evidence_type = "diagnostic_detail"

            if self.check_id == "alt_text":
                selector = "img"
                evidence_type = "selector"
            elif self.check_id == "form_labels":
                selector = "input"
                evidence_type = "selector"
            elif self.check_id == "tech_canonical":
                selector = "link[rel='canonical']"
                evidence_type = "selector"
            elif self.check_id == "tech_meta_title":
                selector = "title"
                evidence_type = "selector"
            elif self.check_id == "tech_meta_desc":
                selector = "meta[name='description']"
                evidence_type = "selector"
            elif self.check_id == "tech_headings":
                selector = "h1"
                evidence_type = "selector"
            elif self.check_id in ("tech_sitemap", "tech_robots_txt", "tech_broken_links", "tech_redirects"):
                evidence_type = "http_trace"

            self.evidence.append(
                ModelEvidence(
                    evidence_id=str(uuid.uuid4()),
                    type=evidence_type,
                    page_url=url,
                    observed_value={"detail": self.detail},
                    selector=selector,
                    captured_at=datetime.now(timezone.utc)
                )
            )




class CheckCategory:
    category_name: str = ""
    category_weight: int = 0

    def __init__(self):
        # Wrap run to store crawl_result on self
        orig_run = self.run
        def wrapped_run(crawl_result, *args, **kwargs):
            self.crawl_result = crawl_result
            return orig_run(crawl_result, *args, **kwargs)
        self.run = wrapped_run

        # Dynamically wrap all _check_ methods to run safely
        for attr_name in dir(self):
            if attr_name.startswith("_check_") and callable(getattr(self, attr_name)):
                orig_method = getattr(self, attr_name)
                setattr(self, attr_name, self._wrap_method(attr_name, orig_method))

    def _wrap_method(self, name, method):
        def wrapped(*args, **kwargs):
            from checks.registry import RULE_REGISTRY, get_rule_metadata
            from checks.base import Severity, CheckResult
            from models import FindingStatus
            
            check_id = name[7:]
            matched_id = (
                check_id if check_id in RULE_REGISTRY
                else next((cid for cid in RULE_REGISTRY if cid.endswith(f"_{check_id}")), check_id)
            )

            crawl_result = getattr(self, "crawl_result", None)
            page_data = None
            
            for arg in args:
                if arg.__class__.__name__ == "PageData":
                    page_data = arg
                elif arg.__class__.__name__ == "CrawlResult":
                    crawl_result = arg
            for k, v in kwargs.items():
                if v.__class__.__name__ == "PageData":
                    page_data = v
                elif v.__class__.__name__ == "CrawlResult":
                    crawl_result = v

            from classifiers import classify_site_type, classify_page_type, classify_location_model

            site_type = "other"
            location_model = None
            if crawl_result:
                if not hasattr(crawl_result, "site_type") or not crawl_result.site_type:
                    crawl_result.site_type = classify_site_type(crawl_result)
                site_type = crawl_result.site_type
                
                if not hasattr(crawl_result, "location_model") or not crawl_result.location_model:
                    crawl_result.location_model = classify_location_model(site_type, crawl_result)
                location_model = crawl_result.location_model
            else:
                site_type = "other"

            page_type = "*"
            depth = 1
            if page_data:
                if not hasattr(page_data, "page_type") or not page_data.page_type:
                    overrides = getattr(crawl_result, "overrides", {}) if crawl_result else {}
                    page_overrides = overrides.get("page_types", {}) if overrides else {}
                    page_data.page_type = classify_page_type(page_data.url, page_data.html, page_data.soup, page_overrides)
                page_type = page_data.page_type
                
                if hasattr(page_data, "depth"):
                    depth = page_data.depth
                else:
                    from urllib.parse import urlparse
                    parsed = urlparse(page_data.url)
                    path = parsed.path.strip("/")
                    depth = len(path.split("/")) if path else 0

            meta = get_rule_metadata(matched_id)
            if meta:
                is_local_seo_check = (meta.category == "Local SEO")
                is_national = (location_model == "national_no_local")
                
                site_app = meta.applicability.get("site_types", ["*"])
                page_app = meta.applicability.get("page_types", ["*"])
                
                site_applicable = False
                for t in site_app:
                    if t == "*":
                        site_applicable = True
                    elif t == "local":
                        if site_type in ("local_service_business", "local_storefront", "multi_location_business"):
                            site_applicable = True
                    elif t == site_type:
                        site_applicable = True
                        
                page_applicable = False
                for t in page_app:
                    if t == "*":
                        page_applicable = True
                    elif t == page_type:
                        page_applicable = True

                applicable = site_applicable and page_applicable
                if is_local_seo_check and is_national:
                    applicable = False

                if not applicable:
                    return CheckResult(
                        check_id=matched_id,
                        check_name=meta.name,
                        category=meta.category,
                        severity=Severity(meta.default_severity),
                        passed=True,
                        score=100,
                        detail="NOT_APPLICABLE",
                        status=FindingStatus.NOT_APPLICABLE
                    )

            try:
                res = method(*args, **kwargs)
                if isinstance(res, CheckResult):
                    # Patch placeholder evidence URLs with the real page/site URL
                    fallback_url = (
                        page_data.url if page_data
                        else crawl_result.homepage.url if crawl_result and crawl_result.homepage
                        else crawl_result.base_url if crawl_result
                        else None
                    )
                    if fallback_url and res.evidence:
                        for ev in res.evidence:
                            if ev.page_url == "https://example.com":
                                ev.page_url = fallback_url
                    if meta:
                        default_sev = res.severity if res.severity else Severity(meta.default_severity)
                            
                        adjusted_sev = default_sev
                        if page_type in ("utility", "policy"):

                            if matched_id == "tech_canonical":
                                adjusted_sev = Severity.LOW
                            else:
                                if default_sev == Severity.CRITICAL:
                                    adjusted_sev = Severity.MEDIUM
                                elif default_sev == Severity.HIGH:
                                    adjusted_sev = Severity.LOW
                                elif default_sev == Severity.MEDIUM:
                                    adjusted_sev = Severity.LOW
                                else:
                                    adjusted_sev = Severity.INFO
                        elif page_type == "homepage":
                            if matched_id == "tech_canonical":
                                adjusted_sev = Severity.HIGH
                        elif depth >= 3:
                            if default_sev == Severity.CRITICAL:
                                adjusted_sev = Severity.HIGH
                            elif default_sev == Severity.HIGH:
                                adjusted_sev = Severity.MEDIUM
                            elif default_sev == Severity.MEDIUM:
                                adjusted_sev = Severity.LOW
                            else:
                                adjusted_sev = Severity.INFO
                                
                        res.severity = adjusted_sev
                        if res.passed:
                            if res.severity == Severity.INFO:
                                res.status = FindingStatus.INFORMATIONAL
                            else:
                                res.status = FindingStatus.PASS
                        else:
                            if res.severity == Severity.INFO:
                                res.status = FindingStatus.INFORMATIONAL
                            elif 0 < res.score < 100:
                                res.status = FindingStatus.WARNING
                            else:
                                res.status = FindingStatus.FAIL
                return res
            except Exception as e:
                meta = get_rule_metadata(matched_id)
                return CheckResult(
                    check_id=matched_id,
                    check_name=meta.name if meta else matched_id,
                    category=meta.category if meta else self.category_name,
                    severity=Severity(meta.default_severity) if meta else Severity.HIGH,
                    passed=False,
                    score=0,
                    detail=f"Error executing check {matched_id}: {e}",
                    status=FindingStatus.ERROR
                )
        return wrapped

    def run(self, crawl_result) -> List[CheckResult]:
        raise NotImplementedError





