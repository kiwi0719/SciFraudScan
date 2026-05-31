from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    check: str
    status: str
    score: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "status": self.status,
            "score": round(float(self.score), 3),
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class SectionReport:
    name: str
    findings: list[Finding]

    @property
    def score(self) -> float:
        if not self.findings:
            return 0.0
        return min(100.0, sum(f.score for f in self.findings) / len(self.findings))

    @property
    def status(self) -> str:
        score = self.score
        if score >= 70:
            return "High Risk"
        if score >= 35:
            return "Warning"
        return "Pass"

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "score": round(self.score, 3),
            "findings": [finding.as_dict() for finding in self.findings],
        }
