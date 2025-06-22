# =============================================================================
# NewsBot Timezone Utilities Module
# =============================================================================
# Timezone utilities for consistent Eastern timezone handling across the 
# application. Automatically handles EST/EDT transitions based on daylight 
# saving time with proper timezone conversion functions.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
from datetime import datetime
from zoneinfo import ZoneInfo

# =============================================================================
# Configuration Constants
# =============================================================================
# Eastern timezone (automatically handles EST/EDT transitions)
EASTERN = ZoneInfo("America/New_York")


# =============================================================================
# Current Time Functions
# =============================================================================
def now_eastern() -> datetime:
    """Get current datetime in Eastern timezone (automatically EST/EDT)."""
    return datetime.now(EASTERN)


# =============================================================================
# Timezone Conversion Functions
# =============================================================================
def utc_to_eastern(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to Eastern timezone."""
    if utc_dt.tzinfo is None:
        # Assume UTC if no timezone info
        utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
    return utc_dt.astimezone(EASTERN)


def eastern_to_utc(eastern_dt: datetime) -> datetime:
    """Convert Eastern datetime to UTC."""
    if eastern_dt.tzinfo is None:
        # Assume Eastern if no timezone info
        eastern_dt = eastern_dt.replace(tzinfo=EASTERN)
    return eastern_dt.astimezone(ZoneInfo("UTC"))


# =============================================================================
# Backward Compatibility Functions (Deprecated)
# =============================================================================
def now_est() -> datetime:
    """Deprecated: Use now_eastern() instead."""
    return now_eastern()


def utc_to_est(utc_dt: datetime) -> datetime:
    """Deprecated: Use utc_to_eastern() instead."""
    return utc_to_eastern(utc_dt)


def est_to_utc(est_dt: datetime) -> datetime:
    """Deprecated: Use eastern_to_utc() instead."""
    return eastern_to_utc(est_dt)
