"""
Remote Administration Cog for VPS Management via Discord

This cog provides comprehensive remote management capabilities for the NewsBot
when running on a VPS, allowing admins to monitor, troubleshoot, and manage
the bot entirely through Discord commands.
"""

import discord
from discord.ext import commands
import asyncio
import subprocess
import psutil
import os
import sys
import traceback
import platform
from datetime import datetime, timedelta
import json
import re
from typing import Optional, Dict, Any
import aiofiles
import shutil

from src.components.decorators.admin_required import admin_required
from src.utils.logger import get_logger
from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.vps_monitor import VPSMonitor

logger = get_logger(__name__)

class RemoteAdminCog(commands.Cog):
    """Remote administration commands for VPS management via Discord."""
    
    def __init__(self, bot):
        self.bot = bot
        self.health_monitor = HealthMonitor()
        self.vps_monitor = VPSMonitor()
        self.command_history = []
        self.max_history = 50
        
    def log_command(self, user: discord.Member, command: str, success: bool = True):
        """Log admin command usage."""
        self.command_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'user': f"{user.display_name} ({user.id})",
            'command': command,
            'success': success
        })
        
        # Keep only recent history
        if len(self.command_history) > self.max_history:
            self.command_history = self.command_history[-self.max_history:]

    @commands.group(name="remote", help="Remote VPS administration commands")
    @admin_required()
    async def remote(self, ctx):
        """Remote administration command group."""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🖥️ Remote VPS Administration",
                description="Available remote management commands:",
                color=discord.Color.blue()
            )
            
            commands_list = [
                "**System Monitoring:**",
                "`/remote status` - Full system status",
                "`/remote resources` - Resource usage (CPU/RAM/Disk)",
                "`/remote processes` - Running processes",
                "`/remote uptime` - System uptime info",
                "",
                "**Log Management:**",
                "`/remote logs [lines]` - View recent logs",
                "`/remote logs_error` - View error logs only",
                "`/remote logs_clear` - Clear old logs",
                "",
                "**Service Control:**",
                "`/remote restart` - Restart bot service",
                "`/remote stop` - Stop bot (emergency only)",
                "`/remote backup` - Create manual backup",
                "`/remote health` - Health check",
                "",
                "**File Management:**",
                "`/remote config_view` - View configuration",
                "`/remote config_backup` - Backup config",
                "`/remote disk_cleanup` - Clean temporary files",
                "",
                "**Emergency Tools:**",
                "`/remote emergency_info` - Emergency diagnostics",
                "`/remote kill_process [name]` - Kill stuck process",
                "`/remote reboot` - Reboot VPS (last resort)",
                "",
                "**Command History:**",
                "`/remote history` - View command history"
            ]
            
            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )
            
            embed.set_footer(text="⚠️ Use with caution - these commands affect the VPS directly")
            await ctx.send(embed=embed)

    @remote.command(name="status")
    async def remote_status(self, ctx):
        """Get comprehensive system status."""
        try:
            self.log_command(ctx.author, "remote status")
            
            # System info
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            # Resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network info
            try:
                network = psutil.net_io_counters()
                network_info = f"Sent: {network.bytes_sent / 1024 / 1024:.1f}MB, Recv: {network.bytes_recv / 1024 / 1024:.1f}MB"
            except:
                network_info = "Network info unavailable"
            
            # Bot-specific status
            health_score = await self.health_monitor.get_health_score()
            
            embed = discord.Embed(
                title="🖥️ VPS System Status",
                color=discord.Color.green() if health_score > 80 else discord.Color.orange()
            )
            
            # System Information
            embed.add_field(
                name="🖥️ System",
                value=f"**OS:** {platform.system()} {platform.release()}\n"
                      f"**Uptime:** {str(uptime).split('.')[0]}\n"
                      f"**Boot Time:** {boot_time.strftime('%Y-%m-%d %H:%M:%S')}",
                inline=True
            )
            
            # Resource Usage
            embed.add_field(
                name="📊 Resources",
                value=f"**CPU:** {cpu_percent}%\n"
                      f"**RAM:** {memory.percent}% ({memory.used / 1024 / 1024 / 1024:.1f}GB)\n"
                      f"**Disk:** {disk.percent}% ({disk.used / 1024 / 1024 / 1024:.1f}GB)",
                inline=True
            )
            
            # Bot Status
            embed.add_field(
                name="🤖 Bot Health",
                value=f"**Health Score:** {health_score}/100\n"
                      f"**Latency:** {round(self.bot.latency * 1000)}ms\n"
                      f"**Guilds:** {len(self.bot.guilds)}",
                inline=True
            )
            
            # Network
            embed.add_field(
                name="🌐 Network",
                value=network_info,
                inline=False
            )
            
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.log_command(ctx.author, "remote status", False)
            await ctx.send(f"❌ Error getting status: {str(e)}")

    @remote.command(name="resources")
    async def remote_resources(self, ctx):
        """Get detailed resource usage."""
        try:
            self.log_command(ctx.author, "remote resources")
            
            # CPU info
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            
            # Memory info
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk info
            disk_usage = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'percent': (usage.used / usage.total) * 100,
                        'free': usage.free / 1024 / 1024 / 1024
                    })
                except:
                    continue
            
            embed = discord.Embed(
                title="📊 Detailed Resource Usage",
                color=discord.Color.blue()
            )
            
            # CPU Details
            cpu_info = f"**Cores:** {cpu_count}\n"
            if cpu_freq:
                cpu_info += f"**Frequency:** {cpu_freq.current:.0f}MHz\n"
            cpu_info += f"**Usage per core:** {', '.join([f'{p:.1f}%' for p in cpu_percent])}"
            
            embed.add_field(
                name="💻 CPU",
                value=cpu_info,
                inline=False
            )
            
            # Memory Details
            memory_info = f"**Total:** {memory.total / 1024 / 1024 / 1024:.1f}GB\n"
            memory_info += f"**Used:** {memory.used / 1024 / 1024 / 1024:.1f}GB ({memory.percent}%)\n"
            memory_info += f"**Available:** {memory.available / 1024 / 1024 / 1024:.1f}GB\n"
            if swap.total > 0:
                memory_info += f"**Swap:** {swap.used / 1024 / 1024 / 1024:.1f}GB / {swap.total / 1024 / 1024 / 1024:.1f}GB"
            
            embed.add_field(
                name="🧠 Memory",
                value=memory_info,
                inline=False
            )
            
            # Disk Details
            if disk_usage:
                disk_info = ""
                for disk in disk_usage:
                    disk_info += f"**{disk['device']}** ({disk['mountpoint']}): {disk['percent']:.1f}% - {disk['free']:.1f}GB free\n"
                
                embed.add_field(
                    name="💾 Disk Usage",
                    value=disk_info,
                    inline=False
                )
            
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.log_command(ctx.author, "remote resources", False)
            await ctx.send(f"❌ Error getting resources: {str(e)}")

    @remote.command(name="logs")
    async def remote_logs(self, ctx, lines: int = 50):
        """View recent log entries."""
        try:
            self.log_command(ctx.author, f"remote logs {lines}")
            
            if lines > 200:
                lines = 200  # Prevent spam
            
            log_file = "logs/NewsBot.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                
                recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
                
                # Split into chunks to avoid Discord message limits
                chunks = []
                current_chunk = ""
                
                for line in recent_logs:
                    if len(current_chunk) + len(line) > 1900:  # Leave room for code blocks
                        chunks.append(current_chunk)
                        current_chunk = line
                    else:
                        current_chunk += line
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                if not chunks:
                    await ctx.send("📄 No logs found.")
                    return
                
                for i, chunk in enumerate(chunks):
                    embed = discord.Embed(
                        title=f"📄 Recent Logs ({i+1}/{len(chunks)})" if len(chunks) > 1 else "📄 Recent Logs",
                        description=f"```\n{chunk}\n```",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Log file not found.")
                
        except Exception as e:
            self.log_command(ctx.author, f"remote logs {lines}", False)
            await ctx.send(f"❌ Error reading logs: {str(e)}")

    @remote.command(name="logs_error")
    async def remote_logs_error(self, ctx, lines: int = 30):
        """View recent error logs only."""
        try:
            self.log_command(ctx.author, f"remote logs_error {lines}")
            
            log_file = "logs/NewsBot.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                
                # Filter for error/warning lines
                error_lines = [
                    line for line in log_lines 
                    if any(level in line.upper() for level in ['ERROR', 'WARNING', 'CRITICAL', 'EXCEPTION'])
                ]
                
                recent_errors = error_lines[-lines:] if len(error_lines) > lines else error_lines
                
                if not recent_errors:
                    embed = discord.Embed(
                        title="✅ No Recent Errors",
                        description="No error or warning logs found in recent entries.",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)
                    return
                
                error_text = ''.join(recent_errors)
                if len(error_text) > 1900:
                    error_text = error_text[-1900:]  # Get most recent
                
                embed = discord.Embed(
                    title="⚠️ Recent Errors/Warnings",
                    description=f"```\n{error_text}\n```",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Log file not found.")
                
        except Exception as e:
            self.log_command(ctx.author, f"remote logs_error {lines}", False)
            await ctx.send(f"❌ Error reading error logs: {str(e)}")

    @remote.command(name="restart")
    async def remote_restart(self, ctx):
        """Restart the bot service."""
        try:
            embed = discord.Embed(
                title="⚠️ Bot Restart Confirmation",
                description="Are you sure you want to restart the bot? This will cause a brief downtime.",
                color=discord.Color.orange()
            )
            
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and reaction.message == message and str(reaction.emoji) in ["✅", "❌"]
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=check)
                
                if str(reaction.emoji) == "✅":
                    self.log_command(ctx.author, "remote restart")
                    
                    restart_embed = discord.Embed(
                        title="🔄 Restarting Bot...",
                        description="The bot is restarting. I'll be back online shortly!",
                        color=discord.Color.yellow()
                    )
                    await ctx.send(embed=restart_embed)
                    
                    # Create restart script and execute
                    restart_script = """#!/bin/bash
sleep 2
if command -v systemctl &> /dev/null; then
    sudo systemctl restart newsbot
else
    pkill -f "python.*run.py"
    sleep 3
    cd /opt/newsbot && nohup python run.py > /dev/null 2>&1 &
fi
"""
                    
                    with open('/tmp/restart_bot.sh', 'w') as f:
                        f.write(restart_script)
                    
                    os.chmod('/tmp/restart_bot.sh', 0o755)
                    subprocess.Popen(['/tmp/restart_bot.sh'], preexec_fn=os.setsid)
                    
                else:
                    await ctx.send("❌ Restart cancelled.")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Restart confirmation timed out.")
                
        except Exception as e:
            self.log_command(ctx.author, "remote restart", False)
            await ctx.send(f"❌ Error during restart: {str(e)}")

    @remote.command(name="backup")
    async def remote_backup(self, ctx):
        """Create a manual backup."""
        try:
            self.log_command(ctx.author, "remote backup")
            
            embed = discord.Embed(
                title="💾 Creating Backup...",
                description="Creating manual backup via remote command.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            
            # Execute backup command
            result = subprocess.run(
                ['python', 'scripts/backup_manager.py', 'create', 'manual'],
                capture_output=True,
                text=True,
                cwd='/opt/newsbot' if os.path.exists('/opt/newsbot') else '.'
            )
            
            if result.returncode == 0:
                success_embed = discord.Embed(
                    title="✅ Backup Created Successfully",
                    description=f"```\n{result.stdout}\n```",
                    color=discord.Color.green()
                )
                await ctx.send(embed=success_embed)
            else:
                error_embed = discord.Embed(
                    title="❌ Backup Failed",
                    description=f"```\n{result.stderr or result.stdout}\n```",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
                
        except Exception as e:
            self.log_command(ctx.author, "remote backup", False)
            await ctx.send(f"❌ Error creating backup: {str(e)}")

    @remote.command(name="processes")
    async def remote_processes(self, ctx):
        """View running processes related to the bot."""
        try:
            self.log_command(ctx.author, "remote processes")
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                try:
                    # Look for bot-related processes
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if any(keyword in cmdline.lower() for keyword in ['newsbot', 'run.py', 'python.*bot']):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu': proc.info['cpu_percent'] or 0,
                            'memory': proc.info['memory_percent'] or 0,
                            'cmd': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not processes:
                embed = discord.Embed(
                    title="🔍 No Bot Processes Found",
                    description="No NewsBot-related processes are currently running.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="🔍 Bot-Related Processes",
                color=discord.Color.blue()
            )
            
            for proc in processes:
                embed.add_field(
                    name=f"PID {proc['pid']} - {proc['name']}",
                    value=f"**CPU:** {proc['cpu']:.1f}% | **Memory:** {proc['memory']:.1f}%\n"
                          f"**Command:** `{proc['cmd']}`",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.log_command(ctx.author, "remote processes", False)
            await ctx.send(f"❌ Error getting processes: {str(e)}")

    @remote.command(name="health")
    async def remote_health(self, ctx):
        """Run comprehensive health check."""
        try:
            self.log_command(ctx.author, "remote health")
            
            embed = discord.Embed(
                title="🏥 Running Health Check...",
                description="Performing comprehensive system health check.",
                color=discord.Color.blue()
            )
            message = await ctx.send(embed=embed)
            
            # Run health check
            health_score = await self.health_monitor.get_health_score()
            health_details = await self.health_monitor.get_health_details()
            
            # Update embed with results
            color = discord.Color.green() if health_score >= 80 else discord.Color.orange() if health_score >= 60 else discord.Color.red()
            
            result_embed = discord.Embed(
                title=f"🏥 Health Check Results - Score: {health_score}/100",
                color=color
            )
            
            # Add health details
            for category, details in health_details.items():
                status_emoji = "✅" if details.get('status') == 'healthy' else "⚠️" if details.get('status') == 'warning' else "❌"
                result_embed.add_field(
                    name=f"{status_emoji} {category.title()}",
                    value=details.get('message', 'No details available'),
                    inline=False
                )
            
            result_embed.timestamp = datetime.utcnow()
            await message.edit(embed=result_embed)
            
        except Exception as e:
            self.log_command(ctx.author, "remote health", False)
            await ctx.send(f"❌ Error during health check: {str(e)}")

    @remote.command(name="emergency_info")
    async def remote_emergency_info(self, ctx):
        """Get emergency diagnostic information."""
        try:
            self.log_command(ctx.author, "remote emergency_info")
            
            emergency_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'system': {
                    'platform': platform.platform(),
                    'python_version': sys.version,
                    'working_directory': os.getcwd(),
                },
                'resources': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent,
                },
                'bot': {
                    'latency': round(self.bot.latency * 1000),
                    'guilds': len(self.bot.guilds),
                    'is_ready': self.bot.is_ready(),
                }
            }
            
            # Check for critical issues
            critical_issues = []
            if emergency_info['resources']['cpu_percent'] > 90:
                critical_issues.append("🔥 CPU usage critically high")
            if emergency_info['resources']['memory_percent'] > 95:
                critical_issues.append("🔥 Memory usage critically high")
            if emergency_info['resources']['disk_percent'] > 95:
                critical_issues.append("🔥 Disk space critically low")
            if emergency_info['bot']['latency'] > 5000:
                critical_issues.append("🔥 Bot latency extremely high")
            
            embed = discord.Embed(
                title="🚨 Emergency Diagnostic Information",
                color=discord.Color.red() if critical_issues else discord.Color.orange()
            )
            
            if critical_issues:
                embed.add_field(
                    name="🔥 Critical Issues Detected",
                    value="\n".join(critical_issues),
                    inline=False
                )
            
            embed.add_field(
                name="💻 System",
                value=f"**Platform:** {emergency_info['system']['platform']}\n"
                      f"**Python:** {emergency_info['system']['python_version'].split()[0]}\n"
                      f"**Working Dir:** {emergency_info['system']['working_directory']}",
                inline=True
            )
            
            embed.add_field(
                name="📊 Resources",
                value=f"**CPU:** {emergency_info['resources']['cpu_percent']}%\n"
                      f"**Memory:** {emergency_info['resources']['memory_percent']}%\n"
                      f"**Disk:** {emergency_info['resources']['disk_percent']}%",
                inline=True
            )
            
            embed.add_field(
                name="🤖 Bot Status",
                value=f"**Ready:** {emergency_info['bot']['is_ready']}\n"
                      f"**Latency:** {emergency_info['bot']['latency']}ms\n"
                      f"**Guilds:** {emergency_info['bot']['guilds']}",
                inline=True
            )
            
            # Recent command history
            if self.command_history:
                recent_commands = self.command_history[-5:]
                command_text = "\n".join([
                    f"`{cmd['timestamp'][:19]}` {cmd['user']}: {cmd['command']} {'✅' if cmd['success'] else '❌'}"
                    for cmd in recent_commands
                ])
                embed.add_field(
                    name="📝 Recent Commands",
                    value=command_text,
                    inline=False
                )
            
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.log_command(ctx.author, "remote emergency_info", False)
            await ctx.send(f"❌ Error getting emergency info: {str(e)}")

    @remote.command(name="history")
    async def remote_history(self, ctx):
        """View command history."""
        try:
            if not self.command_history:
                embed = discord.Embed(
                    title="📝 Command History",
                    description="No commands have been executed yet.",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="📝 Remote Command History",
                color=discord.Color.blue()
            )
            
            # Show recent commands
            recent_commands = self.command_history[-20:]  # Last 20 commands
            command_text = "\n".join([
                f"`{cmd['timestamp'][:19]}` **{cmd['user']}**: {cmd['command']} {'✅' if cmd['success'] else '❌'}"
                for cmd in recent_commands
            ])
            
            embed.add_field(
                name="Recent Commands",
                value=command_text if len(command_text) <= 1024 else command_text[-1024:],
                inline=False
            )
            
            # Summary stats
            total_commands = len(self.command_history)
            successful_commands = sum(1 for cmd in self.command_history if cmd['success'])
            
            embed.add_field(
                name="📊 Statistics",
                value=f"**Total Commands:** {total_commands}\n"
                      f"**Successful:** {successful_commands}\n"
                      f"**Failed:** {total_commands - successful_commands}\n"
                      f"**Success Rate:** {(successful_commands/total_commands*100):.1f}%" if total_commands > 0 else "N/A",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting command history: {str(e)}")

async def setup(bot):
    """Set up the Remote Admin cog."""
    await bot.add_cog(RemoteAdminCog(bot))
    logger.info("Remote Admin cog loaded successfully") 