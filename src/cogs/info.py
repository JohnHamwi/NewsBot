"""
Info Commands Cog

This cog provides information commands for NewsBot.
Handles bot information, features, commands, technologies, and credits.
"""

import traceback
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from src.core.config_manager import config
from src.utils.base_logger import base_logger as logger
from src.utils.structured_logger import structured_logger
from src.components.embeds.base_embed import InfoEmbed, ErrorEmbed

# Configuration constants
GUILD_ID = config.get('bot.guild_id') or 0
__version__ = "2.0.0"  # Bot version


class InfoCommands(commands.Cog):
    """
    Cog for information commands.
    
    Provides comprehensive bot information, features overview,
    command documentation, and credits.
    """

    def __init__(self, bot: discord.Client) -> None:
        """Initialize the InfoCommands cog."""
        self.bot = bot
        logger.debug("🔧 InfoCommands cog initialized")

    @app_commands.command(name="info", description="Show bot information and features")
    @app_commands.describe(
        section="Choose what information to display",
        detailed="Show more detailed information"
    )
    @app_commands.choices(section=[
        app_commands.Choice(name="Overview", value="overview"),
        app_commands.Choice(name="Features", value="features"),
        app_commands.Choice(name="Commands", value="commands"),
        app_commands.Choice(name="Technologies", value="technologies"),
        app_commands.Choice(name="Credits", value="credits"),
    ])
    async def info(
        self, 
        interaction: discord.Interaction, 
        section: app_commands.Choice[str] = None,
        detailed: bool = False
    ) -> None:
        """
        Show comprehensive bot information and features.
        
        Args:
            interaction: The Discord interaction
            section: Choose what information to display
            detailed: Show more detailed information
        """
        try:
            logger.info(f"[INFO][CMD] Info command invoked by user {interaction.user.id}, section={section.value if section else 'overview'}, detailed={detailed}")
            
            # Try to defer if not already responded to
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer(thinking=True)
            except discord.errors.NotFound:
                structured_logger.warning("Interaction already timed out or was responded to")
                return
            
            # Get the selected section or default to overview
            selected_section = section.value if section else "overview"
            
            # Build the appropriate embed based on the selected section
            embed = await self._build_info_embed(selected_section, detailed)
            
            # Send the response
            try:
                await interaction.followup.send(embed=embed)
                logger.info(f"[INFO][CMD] Info command completed successfully for user {interaction.user.id}")
            except discord.errors.NotFound:
                logger.warning("Could not send response, interaction may have expired")
            
        except Exception as e:
            structured_logger.error(
                "Error executing info command",
                extra_data={"error": str(e), "traceback": traceback.format_exc()}
            )
            
            error_embed = ErrorEmbed(
                "Info Command Error",
                f"An error occurred while processing the command: {str(e)}"
            )
            
            try:
                await interaction.followup.send(embed=error_embed)
            except discord.errors.NotFound:
                structured_logger.warning("Could not send error response, interaction may have expired")

    async def _build_info_embed(self, section: str, detailed: bool) -> InfoEmbed:
        """Build the appropriate embed based on the selected section."""
        if section == "overview":
            return await self._build_overview_embed(detailed)
        elif section == "features":
            return await self._build_features_embed(detailed)
        elif section == "commands":
            return await self._build_commands_embed(detailed)
        elif section == "technologies":
            return await self._build_technologies_embed(detailed)
        elif section == "credits":
            return await self._build_credits_embed(detailed)
        else:
            return await self._build_overview_embed(detailed)
    
    async def _build_overview_embed(self, detailed: bool) -> InfoEmbed:
        """Build the overview embed."""
        embed = InfoEmbed(
            "📰 NewsBot Information",
            "NewsBot is a specialized Discord bot for aggregating, translating, and posting "
            "news from Telegram channels to your Discord server. It features automatic content "
            "curation, media handling, and Arabic-to-English translation."
        )
        
        # Get bot metrics for accurate data
        uptime = discord.utils.utcnow() - self.bot.startup_time if hasattr(self.bot, 'startup_time') else None
        uptime_str = str(uptime).split('.')[0] if uptime else "Unknown"
        
        # Bot Details
        bot_details = (
            f"**Name:** {self.bot.user.name}\n"
            f"**ID:** `{self.bot.user.id}`\n"
            f"**Created:** {self.bot.user.created_at.strftime('%Y-%m-%d')}\n"
            f"**Version:** {__version__}\n"
            f"**Uptime:** {uptime_str}\n"
            f"**Serving:** {len(self.bot.guilds)} servers, {sum(guild.member_count or 0 for guild in self.bot.guilds)} users"
        )
        
        embed.add_field(name="🤖 Bot Details", value=bot_details, inline=False)
        
        # Quick stats
        if detailed:
            try:
                cache = self.bot.json_cache
                active_channels = await cache.list_telegram_channels("activated")
                deactivated_channels = await cache.list_telegram_channels("deactivated")
                
                quick_stats = (
                    f"**Active Channels:** {len(active_channels)}\n"
                    f"**Deactivated Channels:** {len(deactivated_channels)}\n"
                    f"**Posting Interval:** {getattr(self.bot, 'auto_post_interval', 'Unknown')}h\n"
                    f"**Last Post:** {getattr(self.bot, 'last_post_time', 'Never')}"
                )
                embed.add_field(name="📊 Quick Stats", value=quick_stats, inline=False)
            except Exception as e:
                logger.error(f"Error gathering quick stats: {e}")
        
        # Usage tip
        usage_tip = (
            "Use `/info section:Features` to see available features\n"
            "Use `/info section:Commands` to see available commands\n"
            "Use `/info section:Technologies` to see technologies used\n"
            "Use `/info section:Credits` to see credits and acknowledgments"
        )
        embed.add_field(name="💡 Usage Tip", value=usage_tip, inline=False)
        
        # Set the bot's avatar as the thumbnail
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            
        return embed
    
    async def _build_features_embed(self, detailed: bool) -> InfoEmbed:
        """Build the features embed."""
        embed = InfoEmbed(
            "✨ NewsBot Features",
            "Discover what NewsBot can do for your server"
        )
        embed.color = discord.Color.green()
        
        # Core Features
        core_features = (
            "• 🔄 **Automatic News Aggregation** - Posts from Telegram channels to Discord\n"
            "• 🌐 **Translation** - Arabic to English translation\n"
            "• 📊 **System Monitoring** - Comprehensive metrics and error tracking\n"
            "• 🛡️ **Error Recovery** - Circuit breakers and automatic recovery\n"
            "• 📋 **Structured Logging** - Detailed JSON-based logging system"
        )
        embed.add_field(name="🚀 Core Features", value=core_features, inline=False)
        
        # Advanced Features
        if detailed:
            advanced_features = (
                "• 🔄 **Round-Robin Posting** - Cycles through channels for variety\n"
                "• 📱 **Rich Presence** - Dynamic status updates with countdown timer\n"
                "• 🕒 **Scheduled Posting** - Configurable intervals for news posting\n"
                "• 🔎 **Content Filtering** - Removes ads and irrelevant content\n"
                "• 📊 **Performance Metrics** - Tracks command usage and latency\n"
                "• 🛡️ **RBAC Security** - Role-based access control for commands\n"
                "• 📈 **Resource Monitoring** - Alerts for high CPU/RAM usage"
            )
            embed.add_field(name="🔥 Advanced Features", value=advanced_features, inline=False)
        
        # Background Tasks
        background_tasks = (
            "• 🔄 **Auto-Posting** - Posts news at configured intervals\n"
            "• 📊 **Metrics Collection** - Gathers system and application metrics\n"
            "• 📝 **Log Tailing** - Sends periodic log summaries\n"
            "• ❤️ **Heartbeat** - Regularly reports system health"
        )
        embed.add_field(name="⚙️ Background Tasks", value=background_tasks, inline=False)
        
        # Set the bot's avatar as the thumbnail
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            
        return embed
    
    async def _build_commands_embed(self, detailed: bool) -> InfoEmbed:
        """Build the commands embed."""
        embed = InfoEmbed(
            "🔧 NewsBot Commands",
            "Here are the available commands you can use"
        )
        embed.color = discord.Color.gold()
        
        # Public Commands
        public_commands = (
            "• `/info` - Show bot information and features (this command!)"
        )
        embed.add_field(name="📝 Public Commands", value=public_commands, inline=False)
        
        # Admin Commands
        admin_commands = (
            "• `/status` - Display comprehensive bot status\n"
            "• `/log` - View recent bot logs\n"
            "• `/config` - Manage bot configuration\n"
            "• `/channel` - Manage Telegram channels\n"
            "• `/set_rich_presence` - Set presence mode\n"
            "• `/set_interval` - Configure auto-posting interval\n"
            "• `/start` - Trigger immediate post\n"
            "• `/test_autopost` - Test auto-posting with delay\n"
            "• `/fix_telegram` - Diagnose Telegram issues"
        )
        embed.add_field(name="👑 Admin Commands", value=admin_commands, inline=False)
        
        if detailed:
            # Command Usage Tips
            usage_tips = (
                "• Most commands have interactive options and choices\n"
                "• Use tab completion to see available parameters\n"
                "• Admin commands require the configured admin role\n"
                "• Commands provide detailed feedback and error messages\n"
                "• Use `/config action:Get Value` to see current settings"
            )
            embed.add_field(name="💡 Usage Tips", value=usage_tips, inline=False)
        
        # Set the bot's avatar as the thumbnail
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            
        return embed
    
    async def _build_technologies_embed(self, detailed: bool) -> InfoEmbed:
        """Build the technologies embed."""
        embed = InfoEmbed(
            "🔧 Technologies Used",
            "NewsBot is built with these technologies"
        )
        embed.color = discord.Color.purple()
        
        # Core Technologies
        core_tech = (
            "• 🐍 **Python 3.9+** - Core programming language\n"
            "• 🎮 **Discord.py** - Discord API wrapper\n"
            "• 📱 **Telethon** - Telegram client library\n"
            "• 🤖 **OpenAI API** - For translation and content analysis\n"
            "• 💾 **JSON Cache** - For data persistence and state management"
        )
        embed.add_field(name="🚀 Core Technologies", value=core_tech, inline=False)
        
        if detailed:
            # Architecture
            architecture = (
                "• 🏗️ **Cogs** - Modular command organization\n"
                "• 🛡️ **Circuit Breakers** - Prevents cascading failures\n"
                "• 🔄 **Task Manager** - Background task coordination\n"
                "• 📊 **Structured Logging** - JSON-based logging system\n"
                "• 🔒 **RBAC** - Role-based access control\n"
                "• 🎨 **Component System** - Reusable UI components"
            )
            embed.add_field(name="🏛️ Architecture", value=architecture, inline=False)
            
            # Development Tools
            dev_tools = (
                "• 🧪 **Pytest** - Testing framework\n"
                "• 🔍 **Pre-commit** - Code quality hooks\n"
                "• 🎨 **Black** - Code formatting\n"
                "• 🔍 **Ruff** - Fast Python linter\n"
                "• 🔒 **Bandit** - Security linting"
            )
            embed.add_field(name="🛠️ Development Tools", value=dev_tools, inline=False)
        
        # System Requirements
        system_req = (
            "• 🖥️ **Python 3.9+**\n"
            "• 🔑 **Discord Bot Token**\n"
            "• 🔑 **Telegram API Credentials**\n"
            "• 🔑 **OpenAI API Key**\n"
            "• 💾 **File System** (for JSON cache)"
        )
        embed.add_field(name="📋 System Requirements", value=system_req, inline=False)
        
        # Set the bot's avatar as the thumbnail
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            
        return embed
    
    async def _build_credits_embed(self, detailed: bool) -> InfoEmbed:
        """Build the credits embed."""
        embed = InfoEmbed(
            "👏 Credits",
            "The people and projects that made NewsBot possible"
        )
        embed.color = discord.Color.magenta()
        
        # Developer info
        admin_user_id = config.get('bot.admin_user_id')
        developer_info = "Unknown developer"
        
        if admin_user_id:
            try:
                user = await self.bot.fetch_user(int(admin_user_id))
                if user:
                    developer_info = f"{user.mention} ({user.name})"
                    if user.display_avatar:
                        embed.set_thumbnail(url=user.display_avatar.url)
            except Exception as e:
                logger.error(f"Failed to fetch admin user: {str(e)}")
                developer_info = f"<@{admin_user_id}>"
        
        embed.add_field(name="👨‍💻 Developer", value=developer_info, inline=False)
        
        # Project Repository
        repository = (
            "🔗 **[View Source Code on GitHub](https://github.com/JohnHamwi/NewsBot)**\n"
            "⭐ Star the repository if you find it useful!\n"
            "🐛 Report issues or contribute improvements"
        )
        embed.add_field(name="📂 Open Source", value=repository, inline=False)
        
        # Libraries and frameworks
        libraries = (
            "• [Discord.py](https://github.com/Rapptz/discord.py)\n"
            "• [Telethon](https://github.com/LonamiWebs/Telethon)\n"
            "• [OpenAI Python](https://github.com/openai/openai-python)\n"
            "• [PyYAML](https://github.com/yaml/pyyaml)\n"
            "• [Psutil](https://github.com/giampaolo/psutil)"
        )
        embed.add_field(name="📚 Libraries", value=libraries, inline=False)
        
        if detailed:
            # Special thanks
            special_thanks = (
                "• Discord Developer Community\n"
                "• Telegram API Developers\n"
                "• Python Community\n"
                "• Open Source Contributors\n"
                "• Claude AI for development assistance"
            )
            embed.add_field(name="💖 Special Thanks", value=special_thanks, inline=False)
        
        # Version and release info
        release_info = f"Version {__version__} - Major Refactor & Optimization"
        embed.add_field(name="🔖 Release", value=release_info, inline=False)
        
        # Footer
        embed.set_footer(text="NewsBot - Bringing news to your Discord server since 2025")
        
        return embed


async def setup(bot: commands.Bot) -> None:
    """Set up the InfoCommands cog."""
    await bot.add_cog(InfoCommands(bot))
    logger.info("✅ InfoCommands cog loaded") 