"""
Timezone utilities for consistent Eastern timezone handling across the application.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# Eastern timezone (automatically handles EST/EDT)
EASTERN = ZoneInfo("America/New_York")


def now_est() -> datetime:
    """Get current datetime in Eastern timezone (EST/EDT)."""
    return datetime.now(EASTERN)


def utc_to_est(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to Eastern timezone."""
    if utc_dt.tzinfo is None:
        # Assume UTC if no timezone info
        utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
    return utc_dt.astimezone(EASTERN)


def est_to_utc(est_dt: datetime) -> datetime:
    """Convert Eastern datetime to UTC."""
    if est_dt.tzinfo is None:
        # Assume Eastern if no timezone info
        est_dt = est_dt.replace(tzinfo=EASTERN)
    return est_dt.astimezone(ZoneInfo("UTC"))
