# =============================================================================
# NewsBot Embeds Package
# =============================================================================
# Standardized embed classes and builders for consistent Discord message formatting
# Last updated: 2025-01-16

# =============================================================================
# Local Application Imports
# =============================================================================
from .base_embed import (
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
