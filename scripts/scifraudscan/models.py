"""Result types.

Deliberately there is no 0-100 "integrity score". A check either finds a
concrete anomaly, finds none, or cannot be run on this input. Collapsing those
into one number invites false precision and lets irrelevant checks dilute a
real signal. See references/METHODOLOGY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Outcome = Literal["flag", "clear", "not_applicable"]
Severity = Literal["high", "moderate", "low"]

_SEVERITY_RANK = {"low": 1, "moderate": 2, "high": 3}


@dataclass(frozen=True)
class Finding:
    """One check's verdict on one input."""

    check: str
    outcome: Outcome
    message: str
    severity: Severity | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome == "flag" and self.severity is None:
            raise ValueError(f"{self.check}: a flag must carry a severity")
        if self.outcome != "flag" and self.severity is not None:
            raise ValueError(f"{self.check}: only a flag may carry a severity")

    @property
    def rank(self) -> int:
        return _SEVERITY_RANK.get(self.severity or "", 0)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "check": self.check,
            "outcome": self.outcome,
            "message": self.message,
        }
        if self.severity is not None:
            payload["severity"] = self.severity
        if self.details:
            payload["details"] = self.details
        return payload


def flag(check: str, severity: Severity, message: str, **details: Any) -> Finding:
    return Finding(check, "flag", message, severity, details)


def clear(check: str, message: str, **details: Any) -> Finding:
    return Finding(check, "clear", message, None, details)


def not_applicable(check: str, reason: str, **details: Any) -> Finding:
    """The check could not run. `reason` must say what the input was missing."""
    return Finding(check, "not_applicable", reason, None, details)
