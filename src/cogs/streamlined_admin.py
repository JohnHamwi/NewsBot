# =============================================================================
# NewsBot Streamlined Admin Commands for Automated Operation
# =============================================================================
# This module provides only essential admin commands for automated NewsBot
# operation, removing unnecessary manual commands and focusing on monitoring
# and emergency controls.
#
# Available Commands:
# - /admin status     - Quick bot status and health monitoring
# - /admin emergency  - Emergency controls (pause/resume/restart/stop)
# - /admin maintenance - Basic maintenance operations
# - /admin info       - Essential bot information
#
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import platform
from datetime import datetime
from typing import Optional

# =============================================================================
# Third-Party Imports  
# =============================================================================
import discord
import psutil
from discord import app_commands
from discord.ext import commands

# =============================================================================
# Local Imports
# =============================================================================
from src.components.embeds.base_embed import BaseEmbed, SuccessEmbed, InfoEmbed, ErrorEmbed
from src.core.unified_config import unified_config as config
from src.utils.base_logger import base_logger as logger
from src.services.enhanced_ai_service import EnhancedAIService


# =============================================================================
# Streamlined Admin Commands Cog
# =============================================================================
class StreamlinedAdminCommands(commands.Cog):
    """
    Essential admin commands for automated NewsBot operation.
    
    This cog provides only the most critical admin functionality needed for
    monitoring and controlling an automated bot. All manual posting commands
    have been removed since the bot operates in full automation mode.
    
    Features:
    - Quick status monitoring for bot health and automation
    - Emergency controls for pause/resume/restart operations  
    - Basic maintenance operations (cache, config, logs, health)
    - Essential bot information display
    """

    def __init__(self, bot):
        """Initialize the StreamlinedAdminCommands cog."""
        self.bot = bot
        self.config = config
        self.enhanced_ai = EnhancedAIService()
        logger.debug("🔧 StreamlinedAdminCommands cog initialized")

    def _is_admin(self, user: discord.Member) -> bool:
        """
        Check if user has admin permissions.
        
        Args:
            user: Discord member to check permissions for
            
        Returns:
            bool: True if user has admin access, False otherwise
        """
        try:
            # Check configured admin role and user IDs
            admin_role_id = self.config.get("production.bot.admin_role_id")
            admin_user_id = self.config.get("production.bot.admin_user_id")
            
            # Check admin role or user ID
            if admin_role_id and any(role.id == admin_role_id for role in user.roles):
                return True
            if admin_user_id and user.id == admin_user_id:
                return True
            return False
        except Exception:
            # Fallback to Discord admin permissions
            return user.guild_permissions.administrator

    # =========================================================================
    # Admin Command Group - Streamlined for Automation
    # =========================================================================
    admin_group = app_commands.Group(
        name="admin", 
        description="🔧 Essential admin controls for automated bot"
    )

    # =========================================================================
    # Essential Status Commands
    # =========================================================================
    @admin_group.command(name="status", description="📊 Quick bot status and health")
    async def status_command(self, interaction: discord.Interaction) -> None:
        """
        Show essential bot status for automated operation.
        
        Displays:
        - Bot online status, uptime, and latency
        - System CPU and memory usage  
        - Automation status and last post time
        """
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # Get basic system information
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Calculate bot uptime
            if hasattr(self.bot, 'start_time'):
                uptime = datetime.now() - self.bot.start_time
                uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            else:
                uptime_str = "Unknown"

            # Create status embed
            embed = InfoEmbed(
                "📊 Bot Status",
                "Essential status for automated operation"
            )

            # Bot status information
            embed.add_field(
                name="🤖 Bot Status",
                value=(
                    f"**Status:** 🟢 Online\n"
                    f"**Uptime:** {uptime_str}\n"
                    f"**Latency:** {round(self.bot.latency * 1000)}ms"
                ),
                inline=True
            )

            # System resource information
            embed.add_field(
                name="🖥️ System",
                value=(
                    f"**CPU:** {cpu_percent}%\n"
                    f"**Memory:** {memory.percent}%\n"
                    f"**Platform:** {platform.system()}"
                ),
                inline=True
            )

            # Automation status information
            automation_enabled = await self.bot.json_cache.get("automation_config.enabled") if hasattr(self.bot, 'json_cache') else True
            last_post = await self.bot.json_cache.get("last_post_time") if hasattr(self.bot, 'json_cache') else None
            
            automation_status = "🟢 Running" if automation_enabled else "🔴 Disabled"
            last_post_str = last_post.split('T')[0] if last_post else "Unknown"
            
            embed.add_field(
                name="🔄 Automation",
                value=(
                    f"**Status:** {automation_status}\n"
                    f"**Last Post:** {last_post_str}\n"
                    f"**Interval:** 3 hours"
                ),
                inline=False
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in status command: {e}")
            error_embed = ErrorEmbed("Status Error", "Failed to get bot status.")
            await interaction.followup.send(embed=error_embed)

    # =========================================================================
    # Emergency Controls
    # =========================================================================
    @admin_group.command(name="emergency", description="🚨 Emergency bot controls")
    @app_commands.describe(action="Emergency action to perform")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="⏸️ Pause Auto-posting", value="pause"),
            app_commands.Choice(name="▶️ Resume Auto-posting", value="resume"),
            app_commands.Choice(name="🔄 Restart Bot", value="restart"),
            app_commands.Choice(name="🛑 Emergency Stop", value="stop"),
        ]
    )
    async def emergency_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str]
    ) -> None:
        """
        Emergency controls for the automated bot.
        
        Available actions:
        - pause: Temporarily disable auto-posting
        - resume: Re-enable auto-posting  
        - restart: Gracefully restart the bot
        - stop: Emergency shutdown of the bot
        """
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            action_value = action.value
            logger.warning(f"🚨 [EMERGENCY] {action_value} command by {interaction.user.id}")

            if action_value == "pause":
                # Pause auto-posting
                success = await self.bot.update_automation_config(enabled=False)
                if success:
                    embed = SuccessEmbed(
                        "⏸️ Auto-posting Paused",
                        "Automatic posting has been temporarily disabled."
                    )
                else:
                    embed = ErrorEmbed("❌ Pause Failed", "Failed to pause auto-posting.")

            elif action_value == "resume":
                # Resume auto-posting
                success = await self.bot.update_automation_config(enabled=True)
                if success:
                    embed = SuccessEmbed(
                        "▶️ Auto-posting Resumed",
                        "Automatic posting has been re-enabled."
                    )
                else:
                    embed = ErrorEmbed("❌ Resume Failed", "Failed to resume auto-posting.")

            elif action_value == "restart":
                # Restart bot
                embed = InfoEmbed(
                    "🔄 Bot Restarting",
                    "Initiating graceful bot restart..."
                )
                await interaction.followup.send(embed=embed)
                
                await asyncio.sleep(2)
                logger.warning("🔄 Emergency restart initiated")
                await self.bot.close()
                return

            elif action_value == "stop":
                # Emergency stop
                embed = InfoEmbed(
                    "🛑 Emergency Stop",
                    "Initiating emergency shutdown..."
                )
                await interaction.followup.send(embed=embed)
                
                await asyncio.sleep(1)
                logger.critical("🛑 Emergency stop initiated")
                await self.bot.close()
                return

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in emergency command: {e}")
            error_embed = ErrorEmbed("Emergency Error", "Failed to execute emergency action.")
            await interaction.followup.send(embed=error_embed)

    # =========================================================================
    # Maintenance Operations
    # =========================================================================
    @admin_group.command(name="maintenance", description="🔧 Basic maintenance operations")
    @app_commands.describe(operation="Maintenance operation to perform")
    @app_commands.choices(
        operation=[
            app_commands.Choice(name="🗑️ Clear Cache", value="clear_cache"),
            app_commands.Choice(name="🔄 Reload Config", value="reload_config"),
            app_commands.Choice(name="📋 View Logs", value="view_logs"),
            app_commands.Choice(name="🛡️ Health Check", value="health_check"),
        ]
    )
    async def maintenance_command(
        self,
        interaction: discord.Interaction,
        operation: app_commands.Choice[str]
    ) -> None:
        """
        Basic maintenance operations for the automated bot.
        
        Available operations:
        - clear_cache: Clear bot's internal cache
        - reload_config: Reload configuration from files
        - view_logs: Display recent log entries
        - health_check: Run comprehensive health check
        """
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("❌ Admin access required.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            operation_value = operation.value
            logger.info(f"🔧 [MAINTENANCE] {operation_value} operation by {interaction.user.id}")

            if operation_value == "clear_cache":
                # Clear cache
                if hasattr(self.bot, 'json_cache') and self.bot.json_cache:
                    # Clear specific cache entries (not all data)
                    cache_keys_to_clear = ["temp_data", "processing_messages", "rate_limits"]
                    cleared_count = 0
                    
                    for key in cache_keys_to_clear:
                        try:
                            await self.bot.json_cache.delete(key)
                            cleared_count += 1
                        except:
                            pass
                    
                    embed = SuccessEmbed(
                        "🗑️ Cache Cleared",
                        f"Cleared {cleared_count} temporary cache entries."
                    )
                else:
                    embed = ErrorEmbed("❌ Cache Error", "Cache system not available.")

            elif operation_value == "reload_config":
                # Reload configuration
                try:
                    success = await self.bot.reload_automation_config()
                    if success:
                        embed = SuccessEmbed(
                            "🔄 Config Reloaded",
                            "Configuration has been reloaded from files."
                        )
                    else:
                        embed = ErrorEmbed("❌ Reload Failed", "Failed to reload configuration.")
                except Exception as e:
                    embed = ErrorEmbed("❌ Reload Error", f"Configuration reload failed: {str(e)}")

            elif operation_value == "view_logs":
                # View recent logs
                try:
                    # Get recent log entries (simplified)
                    log_info = "Recent bot activity:\n"
                    log_info += f"• Uptime: {datetime.now() - self.bot.startup_time if hasattr(self.bot, 'startup_time') else 'Unknown'}\n"
                    log_info += f"• Last restart: {self.bot.startup_time if hasattr(self.bot, 'startup_time') else 'Unknown'}\n"
                    log_info += f"• Status: Operational"
                    
                    embed = InfoEmbed("📋 Recent Logs", log_info)
                except Exception as e:
                    embed = ErrorEmbed("❌ Log Error", "Failed to retrieve log information.")

            elif operation_value == "health_check":
                # Run health check
                try:
                    # Basic health check
                    health_status = "🟢 Healthy"
                    health_details = []
                    
                    # Check bot connection
                    if self.bot.is_ready():
                        health_details.append("✅ Discord connection: OK")
                    else:
                        health_details.append("❌ Discord connection: Failed")
                        health_status = "🔴 Unhealthy"
                    
                    # Check cache system
                    if hasattr(self.bot, 'json_cache') and self.bot.json_cache:
                        health_details.append("✅ Cache system: OK")
                    else:
                        health_details.append("⚠️ Cache system: Not available")
                    
                    # Check automation
                    automation_enabled = await self.bot.json_cache.get("automation_config.enabled") if hasattr(self.bot, 'json_cache') else True
                    if automation_enabled:
                        health_details.append("✅ Automation: Enabled")
                    else:
                        health_details.append("⚠️ Automation: Disabled")
                    
                    embed = InfoEmbed(
                        f"🛡️ Health Check {health_status}",
                        "\n".join(health_details)
                    )
                except Exception as e:
                    embed = ErrorEmbed("❌ Health Check Failed", f"Health check error: {str(e)}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in maintenance command: {e}")
            error_embed = ErrorEmbed("Maintenance Error", "Failed to execute maintenance operation.")
            await interaction.followup.send(embed=error_embed)

    # =========================================================================
    # Bot Information
    # =========================================================================
    @admin_group.command(name="info", description="ℹ️ Basic bot information")
    async def info_command(self, interaction: discord.Interaction) -> None:
        """
        Display basic bot information.
        
        Shows essential information about the bot's configuration,
        automation settings, and operational status.
        """
        await interaction.response.defer()

        try:
            # Create info embed
            embed = InfoEmbed(
                "ℹ️ NewsBot Information",
                "Streamlined automated Syrian news aggregation bot"
            )

            # Bot details
            embed.add_field(
                name="🤖 Bot Details",
                value=(
                    f"**Name:** {self.bot.user.name}\n"
                    f"**ID:** {self.bot.user.id}\n"
                    f"**Version:** Streamlined v4.5.0"
                ),
                inline=True
            )

            # Automation info
            embed.add_field(
                name="🔄 Automation",
                value=(
                    f"**Mode:** Fully Automated\n"
                    f"**Interval:** 3 hours\n"
                    f"**AI Analysis:** Enabled"
                ),
                inline=True
            )

            # Available commands
            embed.add_field(
                name="🎛️ Available Commands",
                value=(
                    f"**Admin Commands:**\n"
                    f"• `/admin status` - Bot status\n"
                    f"• `/admin emergency` - Emergency controls\n"
                    f"• `/admin maintenance` - Maintenance ops\n"
                    f"• `/admin info` - This information"
                ),
                inline=False
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in info command: {e}")
            error_embed = ErrorEmbed("Info Error", "Failed to get bot information.")
            await interaction.followup.send(embed=error_embed)

    @app_commands.command(name="analyze_content", description="🧠 Perform advanced AI content analysis")
    @app_commands.describe(
        content="Content to analyze (news article, social media post, etc.)",
        content_type="Type of content (news, social, announcement)"
    )
    async def analyze_content(self, interaction: discord.Interaction, content: str, content_type: str = "news"):
        """Perform comprehensive AI content analysis."""
        if not self._is_admin(interaction.user):
            return
            
        await interaction.response.defer()
        
        try:
            logger.info(f"🧠 Admin {interaction.user.display_name} requesting content analysis")
            
            # Generate intelligence report
            report = await self.enhanced_ai.get_content_intelligence_report(content)
            
            # Create embed for the report
            embed = discord.Embed(
                title="🧠 Content Intelligence Report",
                description="Advanced AI analysis results",
                color=0x00ff88,
                timestamp=datetime.now()
            )
            
            # Split report into chunks if too long
            if len(report) > 4000:
                # Send first part in embed
                embed.description = report[:4000] + "..."
                await interaction.followup.send(embed=embed)
                
                # Send remaining parts as code blocks
                remaining = report[4000:]
                while remaining:
                    chunk = remaining[:1900]  # Leave room for code block formatting
                    remaining = remaining[1900:]
                    await interaction.followup.send(f"```\n{chunk}\n```")
            else:
                embed.description = report
                await interaction.followup.send(embed=embed)
                
            logger.info(f"✅ Content analysis completed for {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"❌ Content analysis failed: {e}")
            error_embed = discord.Embed(
                title="❌ Analysis Failed",
                description=f"Error during content analysis: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed)
            
    @app_commands.command(name="analyze_message", description="🔍 Analyze a specific message by ID")
    @app_commands.describe(
        message_id="Discord message ID to analyze",
        channel_id="Channel ID (optional, defaults to current channel)"
    )
    async def analyze_message(self, interaction: discord.Interaction, message_id: str, channel_id: str = None):
        """Analyze a specific Discord message."""
        if not self._is_admin(interaction.user):
            return
            
        await interaction.response.defer()
        
        try:
            # Get the channel
            if channel_id:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    await interaction.followup.send("❌ Channel not found")
                    return
            else:
                channel = interaction.channel
                
            # Get the message
            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                await interaction.followup.send("❌ Message not found")
                return
            except discord.Forbidden:
                await interaction.followup.send("❌ No permission to access that message")
                return
                
            if not message.content:
                await interaction.followup.send("❌ Message has no text content to analyze")
                return
                
            logger.info(f"🔍 Analyzing message {message_id} for {interaction.user.display_name}")
            
            # Perform analysis
            analysis = await self.enhanced_ai.analyze_and_optimize_content(message.content, "social")
            
            # Create detailed embed
            embed = discord.Embed(
                title="🔍 Message Analysis Results",
                color=0x00aaff,
                timestamp=datetime.now()
            )
            
            # Add message info
            embed.add_field(
                name="📝 Message Info",
                value=f"Author: {message.author.mention}\nChannel: {channel.mention}\nCreated: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False
            )
            
            # Add analysis summary
            if "summary" in analysis and "overall_score" in analysis["summary"]:
                score = analysis["summary"]["overall_score"]
                score_emoji = "🟢" if score > 0.7 else "🟡" if score > 0.4 else "🔴"
                
                embed.add_field(
                    name="📊 Overall Assessment",
                    value=f"{score_emoji} Score: {score:.1%}",
                    inline=True
                )
                
            # Add key insights
            if analysis.get("advanced_insights"):
                insights = analysis["advanced_insights"]
                summary = await self.enhanced_ai.content_analyzer.get_analysis_summary(insights)
                
                embed.add_field(
                    name="😊 Emotional Profile",
                    value=f"Primary: {summary['emotional_summary']['primary_emotion'].title()}\nIntensity: {summary['emotional_summary']['intensity']}",
                    inline=True
                )
                
                embed.add_field(
                    name="🔍 Credibility",
                    value=f"Score: {summary['credibility_summary']['overall_score']}\nReliability: {summary['credibility_summary']['reliability'].title()}",
                    inline=True
                )
                
                embed.add_field(
                    name="🚀 Viral Potential",
                    value=f"Score: {summary['viral_summary']['viral_potential']}\nSharing: {summary['viral_summary']['sharing_likelihood']}",
                    inline=True
                )
                
            # Add recommendations
            if "summary" in analysis and analysis["summary"].get("action_items"):
                recommendations = "\n".join([f"• {item}" for item in analysis["summary"]["action_items"][:3]])
                embed.add_field(
                    name="💡 Top Recommendations",
                    value=recommendations,
                    inline=False
                )
                
            # Add processing time
            processing_time = analysis.get("processing_time_ms", 0)
            embed.set_footer(text=f"Analysis completed in {processing_time:.0f}ms")
            
            await interaction.followup.send(embed=embed)
            
            logger.info(f"✅ Message analysis completed for {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"❌ Message analysis failed: {e}")
            error_embed = discord.Embed(
                title="❌ Analysis Failed",
                description=f"Error during message analysis: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed)
            
    @app_commands.command(name="content_insights", description="📈 Get content performance insights")
    @app_commands.describe(
        sample_text="Sample text to analyze for optimization insights"
    )
    async def content_insights(self, interaction: discord.Interaction, sample_text: str):
        """Get detailed content optimization insights."""
        if not self._is_admin(interaction.user):
            return
            
        await interaction.response.defer()
        
        try:
            logger.info(f"📈 Generating content insights for {interaction.user.display_name}")
            
            # Perform comprehensive analysis
            analysis = await self.enhanced_ai.analyze_and_optimize_content(sample_text)
            
            # Create insights embed
            embed = discord.Embed(
                title="📈 Content Performance Insights",
                color=0xff6b35,
                timestamp=datetime.now()
            )
            
            # Overall score
            if "summary" in analysis and "overall_score" in analysis["summary"]:
                score = analysis["summary"]["overall_score"]
                score_emoji = "🟢" if score > 0.7 else "🟡" if score > 0.4 else "🔴"
                embed.description = f"**Overall Performance Score:** {score_emoji} {score:.1%}"
                
            # Structure analysis
            if analysis.get("structure_analysis"):
                structure = analysis["structure_analysis"]
                embed.add_field(
                    name="📝 Content Structure",
                    value=f"Words: {structure.get('word_count', 0)}\nSentences: {structure.get('sentence_count', 0)}\nReadability: {structure.get('readability', 'Unknown').title()}",
                    inline=True
                )
                
            # SEO insights
            if analysis.get("seo_insights"):
                seo = analysis["seo_insights"]
                embed.add_field(
                    name="🔍 SEO Analysis",
                    value=f"SEO Score: {seo.get('seo_score', 0):.1%}\nKeyword Density: {seo.get('keyword_density', 0):.1%}\nQuestions: {'Yes' if seo.get('has_questions') else 'No'}",
                    inline=True
                )
                
            # Optimization recommendations
            if analysis.get("optimization"):
                opt = analysis["optimization"]
                all_recommendations = []
                
                for category, recommendations in opt.items():
                    if recommendations:
                        all_recommendations.extend(recommendations[:2])  # Top 2 per category
                        
                if all_recommendations:
                    rec_text = "\n".join([f"• {rec}" for rec in all_recommendations[:5]])
                    embed.add_field(
                        name="🎯 Optimization Recommendations",
                        value=rec_text,
                        inline=False
                    )
                    
            # Advanced insights summary
            if analysis.get("advanced_insights"):
                insights = analysis["advanced_insights"]
                
                embed.add_field(
                    name="🧠 AI Analysis Summary",
                    value=f"Confidence: {insights.confidence_score:.1%}\nProcessing: {insights.processing_time_ms:.0f}ms",
                    inline=True
                )
                
            await interaction.followup.send(embed=embed)
            
            logger.info(f"✅ Content insights generated for {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"❌ Content insights failed: {e}")
            error_embed = discord.Embed(
                title="❌ Insights Failed",
                description=f"Error generating insights: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed)


# =============================================================================
# Cog Setup Function
# =============================================================================
async def setup(bot):
    """Set up the StreamlinedAdminCommands cog."""
    await bot.add_cog(StreamlinedAdminCommands(bot))
    logger.info("✅ StreamlinedAdminCommands cog loaded") 