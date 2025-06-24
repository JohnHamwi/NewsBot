"""
Mobile Admin Cog - Optimized for mobile Discord usage

This cog provides mobile-friendly administrative commands with:
- Quick status commands
- Emergency controls
- Simple troubleshooting
- Easy-to-read output formatted for mobile screens
"""

import discord
from discord.ext import commands, tasks
import asyncio
import subprocess
import psutil
import os
from datetime import datetime, timedelta
import json
from typing import Optional

from src.components.decorators.admin_required import admin_required
from src.utils.logger import get_logger
from src.monitoring.health_monitor import HealthMonitor

logger = get_logger(__name__)

class MobileAdminCog(commands.Cog):
    """Mobile-optimized admin commands for quick VPS management."""
    
    def __init__(self, bot):
        self.bot = bot
        self.health_monitor = HealthMonitor()
        self.last_alert_time = {}
        self.alert_cooldown = 3600  # 1 hour cooldown between same alerts
        
        # Start monitoring task
        self.mobile_monitoring.start()
    
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.mobile_monitoring.cancel()

    @tasks.loop(minutes=10)
    async def mobile_monitoring(self):
        """Background monitoring with mobile alerts."""
        try:
            # Check critical metrics
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            # Get admin user
            admin_user_id = getattr(self.bot, 'admin_user_id', None)
            if not admin_user_id:
                return
            
            admin_user = self.bot.get_user(admin_user_id)
            if not admin_user:
                return
            
            # Check for critical conditions
            alerts = []
            
            if cpu_percent > 90:
                alerts.append(f"🔥 CPU: {cpu_percent:.1f}%")
            elif cpu_percent > 80:
                alerts.append(f"⚠️ CPU: {cpu_percent:.1f}%")
                
            if memory_percent > 95:
                alerts.append(f"🔥 RAM: {memory_percent:.1f}%")
            elif memory_percent > 85:
                alerts.append(f"⚠️ RAM: {memory_percent:.1f}%")
                
            if disk_percent > 95:
                alerts.append(f"🔥 Disk: {disk_percent:.1f}%")
            elif disk_percent > 90:
                alerts.append(f"⚠️ Disk: {disk_percent:.1f}%")
            
            # Send alerts if any
            if alerts:
                alert_key = ','.join(sorted(alerts))
                now = datetime.utcnow()
                
                # Check cooldown
                if alert_key not in self.last_alert_time or \
                   (now - self.last_alert_time[alert_key]).total_seconds() > self.alert_cooldown:
                    
                    embed = discord.Embed(
                        title="🚨 VPS Alert",
                        description="\n".join(alerts),
                        color=discord.Color.red() if any("🔥" in alert for alert in alerts) else discord.Color.orange()
                    )
                    
                    embed.add_field(
                        name="Quick Actions",
                        value="`/q restart` - Restart bot\n"
                              "`/q status` - Check status\n"
                              "`/q logs` - View logs",
                        inline=False
                    )
                    
                    embed.timestamp = now
                    
                    try:
                        await admin_user.send(embed=embed)
                        self.last_alert_time[alert_key] = now
                    except discord.Forbidden:
                        logger.warning("Cannot send DM to admin user")
            
        except Exception as e:
            logger.error(f"Error in mobile monitoring: {e}")

    @mobile_monitoring.before_loop
    async def before_mobile_monitoring(self):
        """Wait for bot to be ready before starting monitoring."""
        await self.bot.wait_until_ready()

    @commands.group(name="q", help="Quick mobile admin commands")
    @admin_required()
    async def quick(self, ctx):
        """Quick admin commands optimized for mobile."""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="📱 Quick Mobile Admin",
                description="Fast commands for mobile management:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🚀 Quick Actions",
                value="`/q status` - System status\n"
                      "`/q health` - Health check\n"
                      "`/q restart` - Restart bot\n"
                      "`/q logs` - Recent logs\n"
                      "`/q errors` - Error logs\n"
                      "`/q backup` - Create backup",
                inline=False
            )
            
            embed.add_field(
                name="🔧 Emergency",
                value="`/q emergency` - Emergency info\n"
                      "`/q fix` - Auto-fix issues\n"
                      "`/q cleanup` - Clean temp files",
                inline=False
            )
            
            await ctx.send(embed=embed)

    @quick.command(name="status", aliases=["s"])
    async def quick_status(self, ctx):
        """Quick system status check."""
        try:
            # Get key metrics
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            uptime_seconds = datetime.now().timestamp() - psutil.boot_time()
            uptime_str = str(timedelta(seconds=int(uptime_seconds))).split('.')[0]
            
            # Health score
            health_score = await self.health_monitor.get_health_score()
            
            # Status emoji
            if health_score >= 90 and cpu < 70 and memory < 80:
                status_emoji = "✅"
                color = discord.Color.green()
            elif health_score >= 70 and cpu < 85 and memory < 90:
                status_emoji = "⚠️"
                color = discord.Color.orange()
            else:
                status_emoji = "🔥"
                color = discord.Color.red()
            
            embed = discord.Embed(
                title=f"{status_emoji} Quick Status",
                color=color
            )
            
            embed.add_field(
                name="📊 Resources",
                value=f"CPU: {cpu:.0f}%\n"
                      f"RAM: {memory:.0f}%\n"
                      f"Disk: {disk:.0f}%",
                inline=True
            )
            
            embed.add_field(
                name="🤖 Bot",
                value=f"Health: {health_score}/100\n"
                      f"Ping: {round(self.bot.latency * 1000)}ms\n"
                      f"Uptime: {uptime_str}",
                inline=True
            )
            
            # Quick actions based on status
            if cpu > 85 or memory > 90:
                embed.add_field(
                    name="🚨 Actions Needed",
                    value="`/q restart` or `/q cleanup`",
                    inline=False
                )
            
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Status error: {str(e)[:100]}")

    @quick.command(name="health", aliases=["h"])
    async def quick_health(self, ctx):
        """Quick health check."""
        try:
            embed = discord.Embed(
                title="🏥 Health Check",
                description="Running quick diagnostic...",
                color=discord.Color.blue()
            )
            message = await ctx.send(embed=embed)
            
            # Get health score and basic checks
            health_score = await self.health_monitor.get_health_score()
            
            # Quick checks
            checks = {
                "Bot Online": self.bot.is_ready(),
                "Discord API": self.bot.latency < 1.0,
                "CPU OK": psutil.cpu_percent() < 90,
                "Memory OK": psutil.virtual_memory().percent < 95,
                "Disk Space": psutil.disk_usage('/').percent < 95
            }
            
            # Create status
            status_lines = []
            all_good = True
            for check_name, result in checks.items():
                emoji = "✅" if result else "❌"
                status_lines.append(f"{emoji} {check_name}")
                if not result:
                    all_good = False
            
            color = discord.Color.green() if all_good else discord.Color.orange()
            
            result_embed = discord.Embed(
                title=f"🏥 Health: {health_score}/100",
                description="\n".join(status_lines),
                color=color
            )
            
            if not all_good:
                result_embed.add_field(
                    name="💡 Quick Fix",
                    value="`/q fix` to auto-resolve issues",
                    inline=False
                )
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            await ctx.send(f"❌ Health check failed: {str(e)[:100]}")

    @quick.command(name="restart", aliases=["r"])
    async def quick_restart(self, ctx):
        """Quick bot restart."""
        try:
            embed = discord.Embed(
                title="⚠️ Restart Bot?",
                description="React ✅ to confirm restart",
                color=discord.Color.orange()
            )
            
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and reaction.message == message and str(reaction.emoji) in ["✅", "❌"]
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=20, check=check)
                
                if str(reaction.emoji) == "✅":
                    restart_embed = discord.Embed(
                        title="🔄 Restarting...",
                        description="Bot will be back online shortly",
                        color=discord.Color.yellow()
                    )
                    await message.edit(embed=restart_embed)
                    
                    # Execute restart
                    restart_script = """#!/bin/bash
sleep 2
if systemctl is-active newsbot >/dev/null 2>&1; then
    sudo systemctl restart newsbot
else
    pkill -f "python.*run.py"
    sleep 3
    cd /opt/newsbot && nohup python run.py > /dev/null 2>&1 &
fi
"""
                    
                    with open('/tmp/quick_restart.sh', 'w') as f:
                        f.write(restart_script)
                    
                    os.chmod('/tmp/quick_restart.sh', 0o755)
                    subprocess.Popen(['/tmp/quick_restart.sh'], preexec_fn=os.setsid)
                    
                else:
                    await message.edit(content="❌ Restart cancelled", embed=None)
                    
            except asyncio.TimeoutError:
                await message.edit(content="⏰ Restart timed out", embed=None)
                
        except Exception as e:
            await ctx.send(f"❌ Restart failed: {str(e)[:100]}")

    @quick.command(name="logs", aliases=["l"])
    async def quick_logs(self, ctx, lines: int = 20):
        """Quick log view."""
        try:
            if lines > 50:
                lines = 50
            
            log_file = "logs/NewsBot.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                
                recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
                log_text = ''.join(recent_logs)
                
                # Truncate for mobile
                if len(log_text) > 1500:
                    log_text = "..." + log_text[-1500:]
                
                embed = discord.Embed(
                    title=f"📄 Last {len(recent_logs)} logs",
                    description=f"```\n{log_text}\n```",
                    color=discord.Color.blue()
                )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No log file found")
                
        except Exception as e:
            await ctx.send(f"❌ Log error: {str(e)[:100]}")

    @quick.command(name="errors", aliases=["e"])
    async def quick_errors(self, ctx):
        """Quick error log view."""
        try:
            log_file = "logs/NewsBot.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                
                # Get recent error lines
                error_lines = [
                    line for line in log_lines[-200:]  # Last 200 lines
                    if any(level in line.upper() for level in ['ERROR', 'CRITICAL', 'EXCEPTION'])
                ]
                
                if not error_lines:
                    embed = discord.Embed(
                        title="✅ No Recent Errors",
                        description="No errors found in recent logs",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Show last few errors
                recent_errors = error_lines[-10:]  # Last 10 errors
                error_text = ''.join(recent_errors)
                
                if len(error_text) > 1500:
                    error_text = "..." + error_text[-1500:]
                
                embed = discord.Embed(
                    title=f"⚠️ Last {len(recent_errors)} errors",
                    description=f"```\n{error_text}\n```",
                    color=discord.Color.red()
                )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No log file found")
                
        except Exception as e:
            await ctx.send(f"❌ Error check failed: {str(e)[:100]}")

    @quick.command(name="backup", aliases=["b"])
    async def quick_backup(self, ctx):
        """Quick backup creation."""
        try:
            embed = discord.Embed(
                title="💾 Creating backup...",
                color=discord.Color.blue()
            )
            message = await ctx.send(embed=embed)
            
            # Create backup
            result = subprocess.run(
                ['python', 'scripts/backup_manager.py', 'create', 'manual'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd='/opt/newsbot' if os.path.exists('/opt/newsbot') else '.'
            )
            
            if result.returncode == 0:
                success_embed = discord.Embed(
                    title="✅ Backup Created",
                    description="Manual backup completed successfully",
                    color=discord.Color.green()
                )
            else:
                success_embed = discord.Embed(
                    title="❌ Backup Failed",
                    description=f"Error: {result.stderr[:200] if result.stderr else 'Unknown error'}",
                    color=discord.Color.red()
                )
            
            await message.edit(embed=success_embed)
            
        except subprocess.TimeoutExpired:
            await ctx.send("⏰ Backup timed out")
        except Exception as e:
            await ctx.send(f"❌ Backup error: {str(e)[:100]}")

    @quick.command(name="emergency", aliases=["sos"])
    async def quick_emergency(self, ctx):
        """Emergency diagnostic info."""
        try:
            # Critical info only
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            embed = discord.Embed(
                title="🚨 Emergency Info",
                color=discord.Color.red()
            )
            
            # Critical metrics
            status = []
            if cpu > 90:
                status.append(f"🔥 CPU: {cpu:.0f}%")
            if memory > 95:
                status.append(f"🔥 RAM: {memory:.0f}%")
            if disk > 95:
                status.append(f"🔥 Disk: {disk:.0f}%")
            
            if not status:
                status.append("✅ All metrics normal")
            
            embed.add_field(
                name="Critical Status",
                value="\n".join(status),
                inline=False
            )
            
            # Bot status
            embed.add_field(
                name="Bot Status",
                value=f"Ready: {self.bot.is_ready()}\n"
                      f"Latency: {round(self.bot.latency * 1000)}ms\n"
                      f"Guilds: {len(self.bot.guilds)}",
                inline=True
            )
            
            # Quick actions
            embed.add_field(
                name="Emergency Actions",
                value="`/q restart` - Restart bot\n"
                      "`/q fix` - Auto-fix\n"
                      "`/q cleanup` - Clean files",
                inline=False
            )
            
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Emergency check failed: {str(e)[:100]}")

    @quick.command(name="fix", aliases=["f"])
    async def quick_fix(self, ctx):
        """Auto-fix common issues."""
        try:
            embed = discord.Embed(
                title="🔧 Auto-fixing issues...",
                color=discord.Color.blue()
            )
            message = await ctx.send(embed=embed)
            
            fixes_applied = []
            
            # Check and fix high CPU
            if psutil.cpu_percent() > 85:
                # Kill any zombie processes
                try:
                    subprocess.run(['pkill', '-f', 'defunct'], timeout=10)
                    fixes_applied.append("✅ Cleaned zombie processes")
                except:
                    pass
            
            # Check and fix high memory
            if psutil.virtual_memory().percent > 90:
                # Clear system cache
                try:
                    subprocess.run(['sync'], timeout=5)
                    with open('/proc/sys/vm/drop_caches', 'w') as f:
                        f.write('3')
                    fixes_applied.append("✅ Cleared system cache")
                except:
                    fixes_applied.append("⚠️ Could not clear cache")
            
            # Check and fix disk space
            if psutil.disk_usage('/').percent > 90:
                # Clean temp files
                try:
                    subprocess.run(['find', '/tmp', '-type', 'f', '-atime', '+7', '-delete'], timeout=30)
                    fixes_applied.append("✅ Cleaned temp files")
                except:
                    pass
                
                # Clean old logs
                try:
                    subprocess.run(['find', 'logs/', '-name', '*.log.*', '-mtime', '+7', '-delete'], timeout=10)
                    fixes_applied.append("✅ Cleaned old logs")
                except:
                    pass
            
            # Check bot health
            if not self.bot.is_ready():
                fixes_applied.append("⚠️ Bot not ready - consider restart")
            elif self.bot.latency > 2.0:
                fixes_applied.append("⚠️ High latency - network issue")
            
            if not fixes_applied:
                fixes_applied.append("✅ No issues found to fix")
            
            result_embed = discord.Embed(
                title="🔧 Auto-fix Complete",
                description="\n".join(fixes_applied),
                color=discord.Color.green()
            )
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            await ctx.send(f"❌ Auto-fix failed: {str(e)[:100]}")

    @quick.command(name="cleanup", aliases=["clean"])
    async def quick_cleanup(self, ctx):
        """Quick cleanup of temporary files."""
        try:
            embed = discord.Embed(
                title="🧹 Cleaning up...",
                color=discord.Color.blue()
            )
            message = await ctx.send(embed=embed)
            
            cleaned = []
            
            # Clean Python cache
            try:
                result = subprocess.run(['find', '.', '-name', '__pycache__', '-type', 'd', '-exec', 'rm', '-rf', '{}', '+'], 
                                      capture_output=True, timeout=30)
                cleaned.append("✅ Python cache")
            except:
                pass
            
            # Clean temp files
            try:
                result = subprocess.run(['find', '/tmp', '-name', 'newsbot*', '-delete'], 
                                      capture_output=True, timeout=30)
                cleaned.append("✅ Temp files")
            except:
                pass
            
            # Clean old session files
            try:
                result = subprocess.run(['find', 'data/sessions/', '-name', '*.session', '-mtime', '+1', '-delete'], 
                                      capture_output=True, timeout=10)
                cleaned.append("✅ Old sessions")
            except:
                pass
            
            result_embed = discord.Embed(
                title="🧹 Cleanup Complete",
                description="\n".join(cleaned) if cleaned else "Nothing to clean",
                color=discord.Color.green()
            )
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            await ctx.send(f"❌ Cleanup failed: {str(e)[:100]}")

async def setup(bot):
    """Set up the Mobile Admin cog."""
    await bot.add_cog(MobileAdminCog(bot))
    logger.info("Mobile Admin cog loaded successfully") 