# =============================================================================
# NewsBot Decorators Package
# =============================================================================
# Reusable decorators for command authorization, rate limiting, and error 
# handling with comprehensive admin permission checks and performance tracking.
# Last updated: 2025-01-16

# =============================================================================
# Local Application Imports
# =============================================================================
from .admin_required import admin_required, admin_required_with_defer

# =============================================================================
# Package Exports
# =============================================================================
__all__ = [
    "admin_required",
    "admin_required_with_defer",
]
