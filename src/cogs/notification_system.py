"""
Notification System Cog

Proactive notification system that keeps admins informed about bot status,
VPS health, errors, and important events through Discord DMs and channels.
Designed for mobile-first administration where admins need immediate alerts.
"""

import discord
from discord.ext import commands, tasks
import asyncio
import json
import psutil
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from src.utils.logger import get_logger
from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.vps_monitor import VPSMonitor

logger = get_logger(__name__)

class NotificationSystem(commands.Cog):
    """Proactive notification system for VPS and bot monitoring."""
    
    def __init__(self, bot):
        self.bot = bot
        self.health_monitor = HealthMonitor()
        self.vps_monitor = VPSMonitor()
        
        # Notification settings
        self.notification_config = {
            'dm_notifications': True,
            'channel_notifications': True,
            'critical_only': False,
            'alert_cooldown': 900,  # 15 minutes between same alerts
            'health_check_interval': 300,  # 5 minutes
            'daily_report_time': '08:00',  # UTC time for daily report
        }
        
        # Alert tracking
        self.last_alerts = {}
        self.alert_history = []
        self.max_alert_history = 200
        
        # Admin contacts
        self.admin_user_id = None
        self.admin_channel_id = None
        self.error_channel_id = None
        
        # Start monitoring tasks
        self.health_monitoring.start()
        self.daily_report.start()
        
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.health_monitoring.cancel()
        self.daily_report.cancel()

    async def initialize_notification_settings(self):
        """Initialize notification settings from bot config."""
        try:
            # Get admin settings from bot config
            if hasattr(self.bot, 'config'):
                config = self.bot.config
                if hasattr(config, 'bot'):
                    self.admin_user_id = getattr(config.bot, 'admin_user_id', None)
                if hasattr(config, 'discord') and hasattr(config.discord, 'channels'):
                    channels = config.discord.channels
                    self.admin_channel_id = getattr(channels, 'logs', None)
                    self.error_channel_id = getattr(channels, 'errors', None)
        except Exception as e:
            logger.error(f"Error initializing notification settings: {e}")

    def log_alert(self, alert_type: str, message: str, severity: str = "info"):
        """Log an alert to history."""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity
        }
        
        self.alert_history.append(alert)
        
        # Keep only recent history
        if len(self.alert_history) > self.max_alert_history:
            self.alert_history = self.alert_history[-self.max_alert_history:]

    async def should_send_alert(self, alert_key: str) -> bool:
        """Check if we should send an alert based on cooldown."""
        now = datetime.utcnow()
        
        if alert_key in self.last_alerts:
            last_alert_time = self.last_alerts[alert_key]
            if (now - last_alert_time).total_seconds() < self.notification_config['alert_cooldown']:
                return False
        
        self.last_alerts[alert_key] = now
        return True

    async def send_admin_dm(self, embed: discord.Embed):
        """Send DM to admin user."""
        if not self.notification_config['dm_notifications'] or not self.admin_user_id:
            return
        
        try:
            admin_user = self.bot.get_user(self.admin_user_id)
            if admin_user:
                await admin_user.send(embed=embed)
                logger.info(f"DM notification sent to admin")
        except discord.Forbidden:
            logger.warning("Cannot send DM to admin - DMs disabled")
        except Exception as e:
            logger.error(f"Error sending admin DM: {e}")

    async def send_channel_notification(self, embed: discord.Embed, channel_type: str = "admin"):
        """Send notification to specified channel."""
        if not self.notification_config['channel_notifications']:
            return
        
        try:
            channel_id = self.admin_channel_id if channel_type == "admin" else self.error_channel_id
            if not channel_id:
                return
            
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)
                logger.info(f"Channel notification sent to {channel_type} channel")
        except Exception as e:
            logger.error(f"Error sending channel notification: {e}")

    async def send_notification(self, embed: discord.Embed, severity: str = "info", dm: bool = True, channel: bool = True):
        """Send notification via DM and/or channel."""
        try:
            # Skip non-critical if in critical-only mode
            if self.notification_config['critical_only'] and severity not in ['critical', 'error']:
                return
            
            # Send DM
            if dm:
                await self.send_admin_dm(embed)
            
            # Send to channel
            if channel:
                channel_type = "error" if severity in ['critical', 'error'] else "admin"
                await self.send_channel_notification(embed, channel_type)
                
        except Exception as e:
            logger.error(f"Error in send_notification: {e}")

    @tasks.loop(minutes=5)
    async def health_monitoring(self):
        """Continuous health monitoring with proactive alerts."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get bot health
            health_score = await self.health_monitor.get_health_score()
            
            # Check for critical conditions
            alerts = []
            
            # CPU alerts
            if cpu_percent > 95:
                if await self.should_send_alert("cpu_critical"):
                    alerts.append({
                        'type': 'cpu_critical',
                        'title': '🔥 Critical CPU Usage',
                        'message': f'CPU usage at {cpu_percent:.1f}% - System may be unresponsive',
                        'severity': 'critical',
                        'color': discord.Color.red(),
                        'actions': ['Check /q status', 'Run /emergency kill_high_cpu', 'Consider /q restart']
                    })
            elif cpu_percent > 85:
                if await self.should_send_alert("cpu_warning"):
                    alerts.append({
                        'type': 'cpu_warning',
                        'title': '⚠️ High CPU Usage',
                        'message': f'CPU usage at {cpu_percent:.1f}% - Monitor closely',
                        'severity': 'warning',
                        'color': discord.Color.orange(),
                        'actions': ['Check /q processes', 'Run /q status']
                    })
            
            # Memory alerts
            if memory.percent > 98:
                if await self.should_send_alert("memory_critical"):
                    alerts.append({
                        'type': 'memory_critical',
                        'title': '🔥 Critical Memory Usage',
                        'message': f'Memory usage at {memory.percent:.1f}% - System at risk',
                        'severity': 'critical',
                        'color': discord.Color.red(),
                        'actions': ['Run /emergency clear_memory', 'Check /q processes', 'Consider restart']
                    })
            elif memory.percent > 90:
                if await self.should_send_alert("memory_warning"):
                    alerts.append({
                        'type': 'memory_warning',
                        'title': '⚠️ High Memory Usage',
                        'message': f'Memory usage at {memory.percent:.1f}% - Consider cleanup',
                        'severity': 'warning',
                        'color': discord.Color.orange(),
                        'actions': ['Run /q cleanup', 'Check /q status']
                    })
            
            # Disk alerts
            if disk.percent > 98:
                if await self.should_send_alert("disk_critical"):
                    alerts.append({
                        'type': 'disk_critical',
                        'title': '🔥 Critical Disk Space',
                        'message': f'Disk usage at {disk.percent:.1f}% - System may fail',
                        'severity': 'critical',
                        'color': discord.Color.red(),
                        'actions': ['Run /emergency disk_emergency', 'Clean logs urgently']
                    })
            elif disk.percent > 95:
                if await self.should_send_alert("disk_warning"):
                    alerts.append({
                        'type': 'disk_warning',
                        'title': '⚠️ Low Disk Space',
                        'message': f'Disk usage at {disk.percent:.1f}% - Cleanup needed',
                        'severity': 'warning',
                        'color': discord.Color.orange(),
                        'actions': ['Run /q cleanup', 'Check log sizes']
                    })
            
            # Bot health alerts
            if health_score < 50:
                if await self.should_send_alert("bot_health_critical"):
                    alerts.append({
                        'type': 'bot_health_critical',
                        'title': '🤖 Bot Health Critical',
                        'message': f'Bot health score: {health_score}/100 - Multiple issues detected',
                        'severity': 'critical',
                        'color': discord.Color.red(),
                        'actions': ['Run /q health', 'Check /q logs', 'Consider /q restart']
                    })
            elif health_score < 70:
                if await self.should_send_alert("bot_health_warning"):
                    alerts.append({
                        'type': 'bot_health_warning',
                        'title': '⚠️ Bot Health Issues',
                        'message': f'Bot health score: {health_score}/100 - Some issues detected',
                        'severity': 'warning',
                        'color': discord.Color.orange(),
                        'actions': ['Run /q health', 'Check /q status']
                    })
            
            # Bot connectivity alerts
            if self.bot.latency > 5.0:
                if await self.should_send_alert("high_latency"):
                    alerts.append({
                        'type': 'high_latency',
                        'title': '🐌 High Bot Latency',
                        'message': f'Bot latency: {round(self.bot.latency * 1000)}ms - Network issues',
                        'severity': 'warning',
                        'color': discord.Color.orange(),
                        'actions': ['Check network connection', 'Monitor for improvements']
                    })
            
            # Send alerts
            for alert in alerts:
                embed = discord.Embed(
                    title=alert['title'],
                    description=alert['message'],
                    color=alert['color']
                )
                
                embed.add_field(
                    name="📱 Quick Actions",
                    value="\n".join(f"• {action}" for action in alert['actions']),
                    inline=False
                )
                
                embed.add_field(
                    name="📊 Current Status",
                    value=f"CPU: {cpu_percent:.1f}%\n"
                          f"RAM: {memory.percent:.1f}%\n"
                          f"Disk: {disk.percent:.1f}%\n"
                          f"Health: {health_score}/100",
                    inline=True
                )
                
                embed.timestamp = datetime.utcnow()
                
                self.log_alert(alert['type'], alert['message'], alert['severity'])
                await self.send_notification(embed, alert['severity'])
            
        except Exception as e:
            logger.error(f"Error in health monitoring: {e}")

    @health_monitoring.before_loop
    async def before_health_monitoring(self):
        """Wait for bot to be ready and initialize settings."""
        await self.bot.wait_until_ready()
        await self.initialize_notification_settings()

    @tasks.loop(time=datetime.strptime("08:00", "%H:%M").time())
    async def daily_report(self):
        """Send daily health and status report."""
        try:
            # Get comprehensive stats
            cpu_avg = psutil.cpu_percent(interval=5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            # Bot stats
            health_score = await self.health_monitor.get_health_score()
            
            # Alert stats from last 24 hours
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            recent_alerts = [
                alert for alert in self.alert_history
                if datetime.fromisoformat(alert['timestamp']) > yesterday
            ]
            
            critical_alerts = len([a for a in recent_alerts if a['severity'] == 'critical'])
            warning_alerts = len([a for a in recent_alerts if a['severity'] == 'warning'])
            
            # Create daily report
            embed = discord.Embed(
                title="📊 Daily VPS & Bot Report",
                description=f"24-hour summary for {now.strftime('%Y-%m-%d')}",
                color=discord.Color.blue()
            )
            
            # System health
            embed.add_field(
                name="💻 System Health",
                value=f"**Uptime:** {str(uptime).split('.')[0]}\n"
                      f"**CPU Avg:** {cpu_avg:.1f}%\n"
                      f"**Memory:** {memory.percent:.1f}%\n"
                      f"**Disk:** {disk.percent:.1f}%",
                inline=True
            )
            
            # Bot health
            embed.add_field(
                name="🤖 Bot Health",
                value=f"**Health Score:** {health_score}/100\n"
                      f"**Avg Latency:** {round(self.bot.latency * 1000)}ms\n"
                      f"**Guilds:** {len(self.bot.guilds)}\n"
                      f"**Status:** {'✅ Healthy' if health_score > 80 else '⚠️ Issues'}",
                inline=True
            )
            
            # Alert summary
            if recent_alerts:
                embed.add_field(
                    name="🚨 24h Alert Summary",
                    value=f"**Critical:** {critical_alerts}\n"
                          f"**Warnings:** {warning_alerts}\n"
                          f"**Total:** {len(recent_alerts)}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="✅ 24h Alert Summary",
                    value="No alerts in last 24 hours\nAll systems stable",
                    inline=True
                )
            
            # Recommendations
            recommendations = []
            if health_score < 80:
                recommendations.append("🔧 Run health check and address issues")
            if memory.percent > 85:
                recommendations.append("🧠 Consider memory cleanup")
            if disk.percent > 90:
                recommendations.append("💾 Disk cleanup recommended")
            if critical_alerts > 0:
                recommendations.append("⚠️ Review critical alerts from yesterday")
            
            if not recommendations:
                recommendations.append("✅ All systems operating normally")
            
            embed.add_field(
                name="💡 Recommendations",
                value="\n".join(recommendations),
                inline=False
            )
            
            embed.set_footer(text="Daily report • Use /q status for current status")
            embed.timestamp = now
            
            await self.send_notification(embed, "info", dm=True, channel=False)
            
        except Exception as e:
            logger.error(f"Error in daily report: {e}")

    @commands.group(name="notify", help="Notification system commands")
    async def notify(self, ctx):
        """Notification system management."""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🔔 Notification System",
                description="Manage proactive notifications and alerts",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📱 Settings",
                value="`/notify settings` - View current settings\n"
                      "`/notify toggle_dm` - Toggle DM notifications\n"
                      "`/notify toggle_channel` - Toggle channel notifications\n"
                      "`/notify critical_only` - Toggle critical-only mode",
                inline=False
            )
            
            embed.add_field(
                name="📊 Information",
                value="`/notify status` - Notification system status\n"
                      "`/notify history` - Recent alert history\n"
                      "`/notify test` - Send test notification",
                inline=False
            )
            
            await ctx.send(embed=embed)

    @notify.command(name="settings")
    async def notify_settings(self, ctx):
        """View notification settings."""
        embed = discord.Embed(
            title="🔔 Notification Settings",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📱 Current Settings",
            value=f"**DM Notifications:** {'✅' if self.notification_config['dm_notifications'] else '❌'}\n"
                  f"**Channel Notifications:** {'✅' if self.notification_config['channel_notifications'] else '❌'}\n"
                  f"**Critical Only:** {'✅' if self.notification_config['critical_only'] else '❌'}\n"
                  f"**Alert Cooldown:** {self.notification_config['alert_cooldown']}s",
            inline=False
        )
        
        embed.add_field(
            name="👤 Admin Contacts",
            value=f"**Admin User:** {f'<@{self.admin_user_id}>' if self.admin_user_id else 'Not set'}\n"
                  f"**Admin Channel:** {f'<#{self.admin_channel_id}>' if self.admin_channel_id else 'Not set'}\n"
                  f"**Error Channel:** {f'<#{self.error_channel_id}>' if self.error_channel_id else 'Not set'}",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @notify.command(name="test")
    async def notify_test(self, ctx):
        """Send test notification."""
        embed = discord.Embed(
            title="🧪 Test Notification",
            description="This is a test notification to verify the notification system is working.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Test Data",
            value=f"**Sent by:** {ctx.author.display_name}\n"
                  f"**Time:** {datetime.utcnow().strftime('%H:%M:%S UTC')}\n"
                  f"**Bot Latency:** {round(self.bot.latency * 1000)}ms",
            inline=False
        )
        
        embed.set_footer(text="Test notification")
        embed.timestamp = datetime.utcnow()
        
        await self.send_notification(embed, "info")
        await ctx.send("✅ Test notification sent!")

    @notify.command(name="history")
    async def notify_history(self, ctx):
        """View recent alert history."""
        if not self.alert_history:
            embed = discord.Embed(
                title="📝 Alert History",
                description="No alerts recorded yet",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return
        
        # Show recent alerts
        recent_alerts = self.alert_history[-20:]  # Last 20 alerts
        
        embed = discord.Embed(
            title="📝 Recent Alert History",
            description=f"Showing last {len(recent_alerts)} alerts:",
            color=discord.Color.blue()
        )
        
        alert_text = ""
        for alert in recent_alerts:
            timestamp = alert['timestamp'][:16].replace('T', ' ')
            severity_emoji = "🔥" if alert['severity'] == 'critical' else "⚠️" if alert['severity'] == 'warning' else "ℹ️"
            alert_text += f"{severity_emoji} `{timestamp}` {alert['type']}: {alert['message'][:50]}...\n"
        
        if len(alert_text) > 1024:
            alert_text = alert_text[-1024:]
        
        embed.add_field(
            name="Recent Alerts",
            value=alert_text,
            inline=False
        )
        
        # Alert summary
        total_alerts = len(self.alert_history)
        critical_count = len([a for a in self.alert_history if a['severity'] == 'critical'])
        warning_count = len([a for a in self.alert_history if a['severity'] == 'warning'])
        
        embed.add_field(
            name="📊 Summary",
            value=f"**Total Alerts:** {total_alerts}\n"
                  f"**Critical:** {critical_count}\n"
                  f"**Warnings:** {warning_count}",
            inline=True
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Set up the Notification System cog."""
    await bot.add_cog(NotificationSystem(bot))
    logger.info("Notification System cog loaded successfully") 