from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class DebtItem:
    path: str
    kind: str  # inline_marker|dep_risk|test_gap|complexity|lint_suppress|churn|generated|deprecated|config_drift
    score: float
    meta: Dict[str, Any] = field(default_factory=dict)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    status: str = "open"
    priority: Optional[str] = None
    owner: Optional[str] = None


@dataclass
class ScanResult:
    repo_root: str
    commit_sha: Optional[str]
    items: List[DebtItem] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)