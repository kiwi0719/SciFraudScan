"""SciFraudScan: statistical screening for research data anomalies."""

from scifraudscan.models import Finding
from scifraudscan.pipeline import CHECK_GROUPS, scan

__all__ = ["CHECK_GROUPS", "Finding", "scan"]
