"""
Embeds Package

Standardized embed classes and builders for consistent Discord message formatting.
"""

from .base_embed import (
    BaseEmbed, SuccessEmbed, ErrorEmbed, WarningEmbed, InfoEmbed,
    StatusEmbed, CommandEmbed, NewsEmbed, ConfigEmbed,
    create_embed_from_template, create_error_embed, create_success_embed
)

__all__ = [
    'BaseEmbed',
    'SuccessEmbed',
    'ErrorEmbed',
    'WarningEmbed',
    'InfoEmbed',
    'StatusEmbed',
    'CommandEmbed',
    'NewsEmbed',
    'ConfigEmbed',
    'create_embed_from_template',
    'create_error_embed',
    'create_success_embed',
]
