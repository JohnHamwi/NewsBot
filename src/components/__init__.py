# =============================================================================
# NewsBot Components Package
# =============================================================================
# Reusable components including decorators, embeds, validators, and formatters
# Last updated: 2025-01-16

# =============================================================================
# Local Application Imports
# =============================================================================
from .decorators.admin_required import admin_required, admin_required_with_defer
from .embeds.base_embed import (
    BaseEmbed,
    CommandEmbed,
    ConfigEmbed,
    ErrorEmbed,
    InfoEmbed,
    NewsEmbed,
    StatusEmbed,
    SuccessEmbed,
    WarningEmbed,
    create_embed_from_template,
    create_error_embed,
    create_success_embed,
)

# =============================================================================
# Package Exports
# =============================================================================
__all__ = [
    # Decorators
    "admin_required",
    "admin_required_with_defer",
    # Embeds
    "BaseEmbed",
    "SuccessEmbed",
    "ErrorEmbed",
    "WarningEmbed",
    "InfoEmbed",
    "StatusEmbed",
    "CommandEmbed",
    "NewsEmbed",
    "ConfigEmbed",
    "create_embed_from_template",
    "create_error_embed",
    "create_success_embed",
]
