import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field

# Schema Version Configuration
schema_version = "2.0.0"

class FindingStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNVERIFIED = "UNVERIFIED"
    ERROR = "ERROR"
    INFORMATIONAL = "INFORMATIONAL"

class AuditRun(BaseModel):
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_url: str
    schema_version: str = "2.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    max_pages: int = 5
    crawl_coverage: float = 1.0

class SiteProfile(BaseModel):
    site_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    site_type: str
    business_model: Optional[str] = None
    locations: List[str] = Field(default_factory=list)
    cms: Optional[str] = None

class PageSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    raw_html_hash: str
    rendered_html_hash: Optional[str] = None
    status_code: int
    headers: dict = Field(default_factory=dict)
    word_count: int = 0
    token_count: int = 0

class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    page_url: str
    observed_value: Any
    selector: Optional[str] = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Finding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    check_id: str
    category: str
    status: FindingStatus
    severity: str
    scope: str
    page_url: Optional[str] = None
    title: str
    observation: str
    applicable: bool = True
    confidence: float = 1.0
    evidence: List[Evidence] = Field(default_factory=list)
    recommendation_id: Optional[str] = None

class Recommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    detail: str
    fix_code: Optional[str] = None
    owner_role: str = "developer"
    estimated_effort: str = "Easy"
    validation_check_id: str

class ScoreSummary(BaseModel):
    overall_score: int
    health_score: float
    coverage_score: float
    confidence_score: float
    opportunity_score: float

class LegacyAuditReport(BaseModel):
    url: str
    score: dict = Field(default_factory=dict)
    checks: List[dict] = Field(default_factory=list)

class MigrationResult(BaseModel):
    schema_version: str = "2.0.0"
    migrated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    audit_run: AuditRun
    site_profile: SiteProfile
    snapshots: List[PageSnapshot] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    score_summary: ScoreSummary

def migrate_legacy_report(legacy_data: dict) -> MigrationResult:
    """Migrates a legacy audit report JSON dictionary to v2.0.0 Pydantic model format."""
    target_url = legacy_data.get("url", "")
    
    # 1. Create AuditRun
    run = AuditRun(target_url=target_url)
    
    # 2. Create SiteProfile
    profile = SiteProfile(site_type="unclassified")
    
    # 3. Score Summary
    legacy_score = legacy_data.get("score", {})
    overall = legacy_score.get("overall_score", 0)
    score_summary = ScoreSummary(
        overall_score=overall,
        health_score=float(overall),
        coverage_score=100.0,
        confidence_score=100.0,
        opportunity_score=0.0
    )
    
    # 4. Findings & Recommendations
    findings_list = []
    recs_list = []
    
    for c in legacy_data.get("checks", []):
        rec_id = str(uuid.uuid4())
        finding_id = str(uuid.uuid4())
        
        # Determine Status Enum
        is_passed = c.get("passed", False)
        status = FindingStatus.PASS if is_passed else FindingStatus.FAIL
        
        # Build Evidence if not passed
        evidence_list = []
        if not is_passed:
            evidence_list.append(
                Evidence(
                    type="diagnostic_detail",
                    page_url=target_url,
                    observed_value={"detail": c.get("detail", "")}
                )
            )
            
        finding = Finding(
            finding_id=finding_id,
            check_id=c.get("check_id", ""),
            category=c.get("category", ""),
            status=status,
            severity=c.get("severity", "info"),
            scope="page",
            page_url=target_url,
            title=c.get("name", ""),
            observation=c.get("detail", ""),
            applicable=True,
            confidence=1.0,
            evidence=evidence_list,
            recommendation_id=rec_id
        )
        findings_list.append(finding)
        
        # Build Recommendation
        rec = Recommendation(
            recommendation_id=rec_id,
            title=f"Fix {c.get('name', '')}",
            detail=c.get("recommendation", "") or "No direct recommendation details available.",
            validation_check_id=c.get("check_id", "")
        )
        recs_list.append(rec)
        
    return MigrationResult(
        schema_version="2.0.0",
        audit_run=run,
        site_profile=profile,
        snapshots=[],
        findings=findings_list,
        recommendations=recs_list,
        score_summary=score_summary
    )
