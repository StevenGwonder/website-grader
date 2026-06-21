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
            import inspect
            import uuid
            from datetime import datetime, timezone
            from models import Evidence as ModelEvidence

            # Find the crawler context in stack
            context = None
            for frame_info in inspect.stack():
                frame = frame_info.frame
                # Look for local variables
                for var_name, var_val in frame.f_locals.items():
                    if var_name in ("page", "crawl_result", "crawl"):
                        context = var_val
                        break
                if context is not None:
                    break

            page_url = "https://example.com"
            selector = None
            observed_value = self.detail
            evidence_type = "diagnostic_detail"

            if context:
                context_class = context.__class__.__name__
                if context_class == "PageData":
                    page_url = context.url
                elif context_class == "CrawlResult":
                    page_url = context.base_url
                    if context.homepage:
                        page_url = context.homepage.url

            # Map selectors for common checks
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
            elif self.check_id == "tech_sitemap":
                evidence_type = "http_trace"
            elif self.check_id == "tech_robots_txt":
                evidence_type = "http_trace"
            elif self.check_id == "tech_broken_links":
                evidence_type = "http_trace"
            elif self.check_id == "tech_redirects":
                evidence_type = "http_trace"

            self.evidence.append(
                ModelEvidence(
                    evidence_id=str(uuid.uuid4()),
                    type=evidence_type,
                    page_url=page_url,
                    observed_value={"detail": observed_value},
                    selector=selector,
                    captured_at=datetime.now(timezone.utc)
                )
            )




class CheckCategory:
    category_name: str = ""
    category_weight: int = 0

    def __init__(self):
        # Dynamically wrap all _check_ methods to run safely
        for attr_name in dir(self):
            if attr_name.startswith("_check_") and callable(getattr(self, attr_name)):
                orig_method = getattr(self, attr_name)
                setattr(self, attr_name, self._wrap_method(attr_name, orig_method))

    def _wrap_method(self, name, method):
        def wrapped(*args, **kwargs):
            from checks.registry import RULE_REGISTRY
            check_id = name[7:]
            matched_id = None
            for cid in RULE_REGISTRY:
                if cid == check_id or cid.endswith(f"_{check_id}") or check_id.endswith(f"_{cid}"):
                    matched_id = cid
                    break
            
            if matched_id is None:
                if check_id == "meta_description": matched_id = "tech_meta_desc"
                elif check_id == "heading_hierarchy": matched_id = "tech_headings"
                elif check_id == "open_graph": matched_id = "tech_og_tags"
                elif check_id == "redirect_chains": matched_id = "tech_redirects"
                elif check_id == "content_uniqueness": matched_id = "content_uniqueness"
                else: matched_id = check_id
            
            try:
                res = method(*args, **kwargs)
                return res
            except Exception as e:
                from checks.base import Severity, CheckResult
                from checks.registry import get_rule_metadata
                from models import FindingStatus
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

    def safe_run_check(self, check_id: str, check_func, *args, **kwargs) -> CheckResult:
        from checks.registry import get_rule_metadata
        meta = get_rule_metadata(check_id)
        try:
            res = check_func(*args, **kwargs)
            return res
        except Exception as e:
            return CheckResult(
                check_id=check_id,
                check_name=meta.name if meta else check_id,
                category=meta.category if meta else self.category_name,
                severity=Severity(meta.default_severity) if meta else Severity.HIGH,
                passed=False,
                score=0,
                detail=f"Error executing check {check_id}: {e}",
                status=FindingStatus.ERROR
            )



