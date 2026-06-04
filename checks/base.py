from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

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
    recommendation: str
    fix_code: Optional[str] = None
    fix_difficulty: str = ""
    impact_estimate: str = ""
    data: dict = field(default_factory=dict)

class CheckCategory:
    category_name: str = ""
    category_weight: int = 0

    def run(self, crawl_result) -> List[CheckResult]:
        raise NotImplementedError
