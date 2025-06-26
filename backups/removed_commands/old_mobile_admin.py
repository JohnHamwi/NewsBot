"""
Mobile Admin Interface for NewsBot
Provides mobile-optimized monitoring and alerting.
"""

import asyncio
import psutil
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any

import discord
from discord.ext import commands, tasks

from src.utils.base_logger import base_logger as logger
from src.components.decorators.admin_required import admin_required_ctx
from src.monitoring.health_monitor import HealthMonitor


class MobileAdminCog(commands.Cog):
    """Mobile-optimized admin interface with monitoring alerts."""
    
    def __init__(self, bot):
        self.bot = bot
        self.health_monitor = HealthMonitor(bot)
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutes
        self.mobile_monitoring.start()

    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        self.mobile_monitoring.cancel()

    @tasks.loop(minutes=10)
    async def mobile_monitoring(self):
        """Background monitoring with mobile alerts."""
        try:
            # Check system health
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            
            # Send alerts for critical conditions
            if cpu > 95:
                await self._send_mobile_alert("🔥 CRITICAL CPU", f"CPU usage: {cpu:.1f}%")
            elif memory > 95:
                await self._send_mobile_alert("🧠 CRITICAL MEMORY", f"Memory usage: {memory:.1f}%")
            
            # Check if bot is responsive
            if not self.bot.is_ready():
                await self._send_mobile_alert("🤖 BOT OFFLINE", "Bot connection lost")
            
        except Exception as e:
            logger.error(f"Error in mobile monitoring: {e}")

    async def _send_mobile_alert(self, title: str, description: str):
        """Send mobile-friendly alert to admin channel."""
        try:
            # Cooldown check
            alert_key = f"{title}_{description}"
            now = datetime.now()
            
            if alert_key in self.last_alert_time:
                time_since_last = (now - self.last_alert_time[alert_key]).total_seconds()
                if time_since_last < self.alert_cooldown:
                    return
            
            self.last_alert_time[alert_key] = now
            
            # Send alert
            from src.core.unified_config import unified_config as config
            logs_channel_id = config.get("discord.channels.logs") or config.get("channels.logs")
            
            if logs_channel_id:
                channel = self.bot.get_channel(logs_channel_id)
                if channel:
                    embed = discord.Embed(
                        title=f"📱 {title}",
                        description=description,
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    await channel.send(embed=embed)
                    
        except Exception as e:
            logger.error(f"Error sending mobile alert: {e}")

    @mobile_monitoring.before_loop
    async def before_mobile_monitoring(self):
        """Wait for bot to be ready before starting monitoring."""
        await self.bot.wait_until_ready()


async def setup(bot):
    """Add the mobile admin cog."""
    await bot.add_cog(MobileAdminCog(bot))
    logger.info("Mobile Admin cog loaded successfully") 