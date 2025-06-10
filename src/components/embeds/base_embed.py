"""
Base Embed Components

Provides standardized embed classes and builders to ensure consistent
formatting and styling across all bot embeds.
"""

import discord
from datetime import datetime
from typing import Optional, Union, List, Dict, Any
from src.core.config_manager import config


class BaseEmbed(discord.Embed):
    """
    Base embed class with consistent styling and footer.

    Provides standardized formatting for all bot embeds including
    consistent colors, timestamps, and footer information.
    """

    def __init__(
        self,
        title: str,
        description: str = None,
        color: Union[discord.Color, int] = None,
        timestamp: datetime = None
    ):
        """
        Initialize a base embed with standard formatting.

        Args:
            title: The embed title
            description: The embed description (optional)
            color: The embed color (defaults to blue)
            timestamp: The embed timestamp (defaults to current time)
        """
        super().__init__(
            title=title,
            description=description,
            color=color or discord.Color.blue(),
            timestamp=timestamp or discord.utils.utcnow()
        )

        # Set standard footer
        bot_version = config.get('bot.version', '2.0.0')
        self.set_footer(
            text=f"NewsBot v{bot_version}",
            icon_url="https://cdn.discordapp.com/attachments/placeholder/newsbot-icon.png"
        )


class SuccessEmbed(BaseEmbed):
    """Embed for successful operations."""

    def __init__(self, title: str, description: str = None):
        super().__init__(title, description, discord.Color.green())


class ErrorEmbed(BaseEmbed):
    """Embed for error messages."""

    def __init__(self, title: str, description: str = None):
        super().__init__(title, description, discord.Color.red())


class WarningEmbed(BaseEmbed):
    """Embed for warning messages."""

    def __init__(self, title: str, description: str = None):
        super().__init__(title, description, discord.Color.orange())


class InfoEmbed(BaseEmbed):
    """Embed for informational messages."""

    def __init__(self, title: str, description: str = None):
        super().__init__(title, description, discord.Color.blue())


class StatusEmbed(BaseEmbed):
    """
    Specialized embed for status information.

    Provides methods for adding status fields with consistent formatting.
    """

    def __init__(self, title: str = "📊 Bot Status", description: str = None):
        super().__init__(title, description, discord.Color.blue())

    def add_status_field(
        self,
        name: str,
        value: Any,
        inline: bool = True,
        format_as_code: bool = True
    ) -> 'StatusEmbed':
        """
        Add a status field with consistent formatting.

        Args:
            name: Field name
            value: Field value
            inline: Whether field should be inline
            format_as_code: Whether to format value as code block

        Returns:
            Self for method chaining
        """
        if format_as_code:
            formatted_value = f"```{value}```"
        else:
            formatted_value = str(value)

        self.add_field(name=name, value=formatted_value, inline=inline)
        return self

    def add_metric(
        self,
        name: str,
        value: Union[str, int, float],
        unit: str = "",
        inline: bool = True
    ) -> 'StatusEmbed':
        """
        Add a metric field with proper formatting.

        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            inline: Whether field should be inline

        Returns:
            Self for method chaining
        """
        formatted_value = f"```{value}{unit}```"
        self.add_field(name=name, value=formatted_value, inline=inline)
        return self


class CommandEmbed(BaseEmbed):
    """
    Specialized embed for command responses.

    Provides methods for adding command-specific information.
    """

    def __init__(self, command_name: str, description: str = None):
        title = f"🎮 Command: {command_name}"
        super().__init__(title, description)

    def add_parameter(
        self,
        name: str,
        value: Any,
        required: bool = False
    ) -> 'CommandEmbed':
        """
        Add a command parameter field.

        Args:
            name: Parameter name
            value: Parameter value
            required: Whether parameter is required

        Returns:
            Self for method chaining
        """
        indicator = "🔴" if required else "🟢"
        field_name = f"{indicator} {name}"
        self.add_field(name=field_name, value=f"```{value}```", inline=True)
        return self


class NewsEmbed(BaseEmbed):
    """
    Specialized embed for news posts.

    Provides methods for formatting news content consistently.
    """

    def __init__(self, title: str, description: str = None):
        super().__init__(title, description, discord.Color.gold())

    def set_news_content(
        self,
        content: str,
        source: str = None,
        timestamp: datetime = None
    ) -> 'NewsEmbed':
        """
        Set the main news content.

        Args:
            content: News content
            source: News source
            timestamp: News timestamp

        Returns:
            Self for method chaining
        """
        if len(content) > 4096:
            content = content[:4093] + "..."

        self.description = content

        if source:
            self.add_field(name="📰 Source", value=source, inline=True)

        if timestamp:
            self.add_field(
                name="🕒 Published",
                value=timestamp.strftime("%Y-%m-%d %H:%M UTC"),
                inline=True
            )

        return self

    def add_media_info(self, media_count: int, media_types: List[str] = None) -> 'NewsEmbed':
        """
        Add media information to the embed.

        Args:
            media_count: Number of media items
            media_types: Types of media (photo, video, etc.)

        Returns:
            Self for method chaining
        """
        if media_count > 0:
            media_text = f"{media_count} item(s)"
            if media_types:
                media_text += f" ({', '.join(media_types)})"

            self.add_field(name="📎 Media", value=media_text, inline=True)

        return self


class ConfigEmbed(BaseEmbed):
    """
    Specialized embed for configuration information.

    Provides methods for displaying configuration data.
    """

    def __init__(self, title: str = "⚙️ Configuration", description: str = None):
        super().__init__(title, description, discord.Color.purple())

    def add_config_section(
        self,
        section_name: str,
        config_data: Dict[str, Any]
    ) -> 'ConfigEmbed':
        """
        Add a configuration section.

        Args:
            section_name: Name of the configuration section
            config_data: Configuration data dictionary

        Returns:
            Self for method chaining
        """
        config_text = []
        for key, value in config_data.items():
            config_text.append(f"{key}: {value}")

        formatted_text = "```\n" + "\n".join(config_text) + "\n```"
        self.add_field(name=section_name, value=formatted_text, inline=False)
        return self


def create_embed_from_template(
    template_type: str,
    title: str,
    description: str = None,
    **kwargs
) -> BaseEmbed:
    """
    Factory function to create embeds from templates.

    Args:
        template_type: Type of embed to create
        title: Embed title
        description: Embed description
        **kwargs: Additional arguments for specific embed types

    Returns:
        Appropriate embed instance
    """
    embed_classes = {
        'success': SuccessEmbed,
        'error': ErrorEmbed,
        'warning': WarningEmbed,
        'info': InfoEmbed,
        'status': StatusEmbed,
        'command': CommandEmbed,
        'news': NewsEmbed,
        'config': ConfigEmbed,
        'base': BaseEmbed
    }

    embed_class = embed_classes.get(template_type, BaseEmbed)

    if template_type == 'command':
        return embed_class(title, description)
    else:
        return embed_class(title, description)


# Utility functions for common embed patterns
def create_error_embed(title: str, error: Exception, context: str = None) -> ErrorEmbed:
    """
    Create a standardized error embed.

    Args:
        title: Error title
        error: Exception object
        context: Additional context information

    Returns:
        Formatted error embed
    """
    description = f"**Error:** {str(error)}"
    if context:
        description += f"\n**Context:** {context}"

    embed = ErrorEmbed(title, description)
    embed.add_field(
        name="🔧 Need Help?",
        value="Contact an administrator if this error persists.",
        inline=False
    )

    return embed


def create_success_embed(title: str, message: str, details: Dict[str, Any] = None) -> SuccessEmbed:
    """
    Create a standardized success embed.

    Args:
        title: Success title
        message: Success message
        details: Additional details to display

    Returns:
        Formatted success embed
    """
    embed = SuccessEmbed(title, message)

    if details:
        for key, value in details.items():
            embed.add_field(name=key, value=f"```{value}```", inline=True)

    return embed
