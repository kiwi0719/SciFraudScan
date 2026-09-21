"""SciFraudScan: statistical screening for research data anomalies."""

from scifraudscan._version import __version__
from scifraudscan.models import Finding
from scifraudscan.pipeline import CHECK_GROUPS, scan

__all__ = ["CHECK_GROUPS", "Finding", "__version__", "scan"]
