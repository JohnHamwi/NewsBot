"""
Emergency Controls Cog

Critical emergency commands for VPS management when immediate action is needed.
These commands are designed to be used when the bot or VPS is experiencing
severe issues and requires immediate intervention.
"""

import discord
from discord.ext import commands
import asyncio
import subprocess
import psutil
import os
import signal
import json
from datetime import datetime, timedelta
from typing import Optional

from src.components.decorators.admin_required import admin_required
from src.utils.logger import get_logger

logger = get_logger(__name__)

class EmergencyControlsCog(commands.Cog):
    """Emergency control commands for critical VPS situations."""
    
    def __init__(self, bot):
        self.bot = bot
        self.emergency_log = []
        self.max_emergency_log = 100
        
    def log_emergency(self, user: discord.Member, action: str, details: str = ""):
        """Log emergency actions."""
        self.emergency_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'user': f"{user.display_name} ({user.id})",
            'action': action,
            'details': details
        })
        
        # Keep only recent history
        if len(self.emergency_log) > self.max_emergency_log:
            self.emergency_log = self.emergency_log[-self.max_emergency_log:]
        
        # Log to file as well
        logger.critical(f"EMERGENCY ACTION by {user.display_name}: {action} - {details}")

    @commands.group(name="emergency", aliases=["sos"], help="Emergency VPS control commands")
    @admin_required()
    async def emergency(self, ctx):
        """Emergency control commands."""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🚨 Emergency Controls",
                description="**⚠️ CRITICAL COMMANDS - USE WITH EXTREME CAUTION ⚠️**",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="🔥 Immediate Actions",
                value="`/emergency kill_high_cpu` - Kill high CPU processes\n"
                      "`/emergency force_restart` - Force bot restart\n"
                      "`/emergency clear_memory` - Emergency memory cleanup\n"
                      "`/emergency shutdown_safe` - Safe bot shutdown",
                inline=False
            )
            
            embed.add_field(
                name="💻 System Controls",
                value="`/emergency reboot_vps` - Reboot entire VPS\n"
                      "`/emergency kill_process <pid>` - Kill specific process\n"
                      "`/emergency disk_emergency` - Emergency disk cleanup\n"
                      "`/emergency network_reset` - Reset network config",
                inline=False
            )
            
            embed.add_field(
                name="📊 Diagnostics",
                value="`/emergency system_info` - Critical system info\n"
                      "`/emergency process_tree` - Show process tree\n"
                      "`/emergency emergency_log` - View emergency log\n"
                      "`/emergency last_resort` - Nuclear option info",
                inline=False
            )
            
            embed.set_footer(text="⚠️ These commands can affect system stability. Document usage in #admin-logs")
            await ctx.send(embed=embed)

    @emergency.command(name="kill_high_cpu")
    async def emergency_kill_high_cpu(self, ctx):
        """Kill processes using excessive CPU."""
        try:
            embed = discord.Embed(
                title="⚠️ Kill High CPU Processes?",
                description="This will kill processes using >90% CPU\n"
                           "React ✅ to confirm",
                color=discord.Color.orange()
            )
            
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and reaction.message == message and str(reaction.emoji) in ["✅", "❌"]
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=15, check=check)
                
                if str(reaction.emoji) == "✅":
                    high_cpu_processes = []
                    killed_processes = []
                    
                    # Find high CPU processes
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                        try:
                            cpu_percent = proc.info['cpu_percent'] or 0
                            if cpu_percent > 90 and proc.info['pid'] != os.getpid():  # Don't kill ourselves
                                high_cpu_processes.append(proc.info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    if not high_cpu_processes:
                        await message.edit(embed=discord.Embed(
                            title="✅ No High CPU Processes",
                            description="No processes found using >90% CPU",
                            color=discord.Color.green()
                        ))
                        return
                    
                    # Kill high CPU processes
                    for proc_info in high_cpu_processes:
                        try:
                            proc = psutil.Process(proc_info['pid'])
                            proc.terminate()
                            killed_processes.append(f"{proc_info['name']} (PID: {proc_info['pid']})")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    self.log_emergency(ctx.author, "kill_high_cpu", f"Killed {len(killed_processes)} processes")
                    
                    result_embed = discord.Embed(
                        title="🔥 High CPU Processes Killed",
                        description=f"Killed {len(killed_processes)} processes:\n" + "\n".join(killed_processes[:10]),
                        color=discord.Color.yellow()
                    )
                    
                    await message.edit(embed=result_embed)
                    
                else:
                    await message.edit(embed=discord.Embed(
                        title="❌ Action Cancelled",
                        color=discord.Color.blue()
                    ))
                    
            except asyncio.TimeoutError:
                await message.edit(embed=discord.Embed(
                    title="⏰ Action Timed Out",
                    color=discord.Color.grey()
                ))
                
        except Exception as e:
            await ctx.send(f"❌ Error in emergency CPU kill: {str(e)}")

    @emergency.command(name="force_restart")
    async def emergency_force_restart(self, ctx):
        """Force restart the bot with immediate effect."""
        try:
            embed = discord.Embed(
                title="🔥 FORCE RESTART BOT?",
                description="**This will immediately restart the bot**\n"
                           "No graceful shutdown - emergency only!\n\n"
                           "React ✅ to confirm",
                color=discord.Color.red()
            )
            
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and reaction.message == message and str(reaction.emoji) in ["✅", "❌"]
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
                
                if str(reaction.emoji) == "✅":
                    self.log_emergency(ctx.author, "force_restart", "Emergency force restart initiated")
                    
                    await message.edit(embed=discord.Embed(
                        title="🔥 FORCE RESTARTING NOW",
                        description="Bot will restart immediately!",
                        color=discord.Color.red()
                    ))
                    
                    # Force restart without graceful shutdown
                    force_restart_script = """#!/bin/bash
sleep 1
pkill -9 -f "python.*run.py"
sleep 2
if systemctl is-active newsbot >/dev/null 2>&1; then
    sudo systemctl restart newsbot
else
    cd /opt/newsbot && nohup python run.py > /dev/null 2>&1 &
fi
"""
                    
                    with open('/tmp/force_restart.sh', 'w') as f:
                        f.write(force_restart_script)
                    
                    os.chmod('/tmp/force_restart.sh', 0o755)
                    subprocess.Popen(['/tmp/force_restart.sh'], preexec_fn=os.setsid)
                    
                else:
                    await message.edit(embed=discord.Embed(
                        title="❌ Force Restart Cancelled",
                        color=discord.Color.blue()
                    ))
                    
            except asyncio.TimeoutError:
                await message.edit(embed=discord.Embed(
                    title="⏰ Force Restart Timed Out",
                    color=discord.Color.grey()
                ))
                
        except Exception as e:
            await ctx.send(f"❌ Error in force restart: {str(e)}")

    @emergency.command(name="clear_memory")
    async def emergency_clear_memory(self, ctx):
        """Emergency memory cleanup."""
        try:
            memory_before = psutil.virtual_memory().percent
            
            embed = discord.Embed(
                title="🧠 Emergency Memory Cleanup",
                description=f"Current memory usage: {memory_before:.1f}%\n"
                           "Clearing system memory...",
                color=discord.Color.blue()
            )
            message = await ctx.send(embed=embed)
            
            cleanup_results = []
            
            # Force garbage collection in Python
            import gc
            gc.collect()
            cleanup_results.append("✅ Python garbage collection")
            
            # Clear system caches
            try:
                subprocess.run(['sync'], timeout=10)
                with open('/proc/sys/vm/drop_caches', 'w') as f:
                    f.write('3')
                cleanup_results.append("✅ System cache cleared")
            except:
                cleanup_results.append("❌ Could not clear system cache")
            
            # Clear swap if possible
            try:
                subprocess.run(['swapoff', '-a'], timeout=30)
                subprocess.run(['swapon', '-a'], timeout=30)
                cleanup_results.append("✅ Swap cleared")
            except:
                cleanup_results.append("⚠️ Could not clear swap")
            
            memory_after = psutil.virtual_memory().percent
            memory_saved = memory_before - memory_after
            
            self.log_emergency(ctx.author, "clear_memory", f"Saved {memory_saved:.1f}% memory")
            
            result_embed = discord.Embed(
                title="🧠 Memory Cleanup Complete",
                description=f"Memory usage: {memory_before:.1f}% → {memory_after:.1f}%\n"
                           f"Saved: {memory_saved:.1f}%\n\n" + "\n".join(cleanup_results),
                color=discord.Color.green() if memory_saved > 0 else discord.Color.orange()
            )
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error in memory cleanup: {str(e)}")

    @emergency.command(name="kill_process")
    async def emergency_kill_process(self, ctx, pid: int):
        """Kill a specific process by PID."""
        try:
            # Check if process exists
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
                proc_cpu = proc.cpu_percent()
                proc_memory = proc.memory_percent()
            except psutil.NoSuchProcess:
                await ctx.send(f"❌ Process with PID {pid} not found")
                return
            
            # Don't allow killing the bot itself
            if pid == os.getpid():
                await ctx.send("❌ Cannot kill the bot process itself")
                return
            
            embed = discord.Embed(
                title=f"⚠️ Kill Process {pid}?",
                description=f"**Process:** {proc_name}\n"
                           f"**CPU:** {proc_cpu:.1f}%\n"
                           f"**Memory:** {proc_memory:.1f}%\n\n"
                           "React ✅ to confirm",
                color=discord.Color.orange()
            )
            
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and reaction.message == message and str(reaction.emoji) in ["✅", "❌"]
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=15, check=check)
                
                if str(reaction.emoji) == "✅":
                    try:
                        proc.terminate()
                        # Wait for graceful termination
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        # Force kill if doesn't terminate gracefully
                        proc.kill()
                    
                    self.log_emergency(ctx.author, "kill_process", f"Killed {proc_name} (PID: {pid})")
                    
                    await message.edit(embed=discord.Embed(
                        title=f"💀 Process {pid} Killed",
                        description=f"Successfully killed {proc_name}",
                        color=discord.Color.red()
                    ))
                    
                else:
                    await message.edit(embed=discord.Embed(
                        title="❌ Process Kill Cancelled",
                        color=discord.Color.blue()
                    ))
                    
            except asyncio.TimeoutError:
                await message.edit(embed=discord.Embed(
                    title="⏰ Process Kill Timed Out",
                    color=discord.Color.grey()
                ))
                
        except Exception as e:
            await ctx.send(f"❌ Error killing process: {str(e)}")

    @emergency.command(name="system_info")
    async def emergency_system_info(self, ctx):
        """Get critical system information for diagnostics."""
        try:
            # Get critical system info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            # Get top processes
            top_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 5:
                        top_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            top_processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            top_processes = top_processes[:5]  # Top 5
            
            embed = discord.Embed(
                title="🚨 Critical System Information",
                color=discord.Color.red()
            )
            
            # System status
            embed.add_field(
                name="💻 System Status",
                value=f"**Uptime:** {str(uptime).split('.')[0]}\n"
                      f"**Boot Time:** {boot_time.strftime('%H:%M:%S')}\n"
                      f"**Load Avg:** {', '.join(map(str, os.getloadavg()))[:15]}",
                inline=True
            )
            
            # Resource usage
            embed.add_field(
                name="📊 Resources",
                value=f"**CPU:** {cpu_percent:.1f}%\n"
                      f"**Memory:** {memory.percent:.1f}%\n"
                      f"**Disk:** {disk.percent:.1f}%",
                inline=True
            )
            
            # Top processes
            if top_processes:
                proc_text = "\n".join([
                    f"`{proc['pid']}` {proc['name'][:15]} - {proc['cpu_percent']:.1f}%"
                    for proc in top_processes
                ])
                embed.add_field(
                    name="🔥 Top CPU Processes",
                    value=proc_text,
                    inline=False
                )
            
            # Bot specific info
            embed.add_field(
                name="🤖 Bot Status",
                value=f"**Ready:** {self.bot.is_ready()}\n"
                      f"**Latency:** {round(self.bot.latency * 1000)}ms\n"
                      f"**PID:** {os.getpid()}",
                inline=True
            )
            
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting system info: {str(e)}")

    @emergency.command(name="emergency_log")
    async def emergency_log_view(self, ctx):
        """View emergency action log."""
        try:
            if not self.emergency_log:
                embed = discord.Embed(
                    title="📝 Emergency Log",
                    description="No emergency actions recorded",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                return
            
            # Show recent emergency actions
            recent_actions = self.emergency_log[-10:]  # Last 10 actions
            
            embed = discord.Embed(
                title="📝 Emergency Action Log",
                description=f"Showing last {len(recent_actions)} emergency actions:",
                color=discord.Color.orange()
            )
            
            for action in recent_actions:
                timestamp = action['timestamp'][:19].replace('T', ' ')
                embed.add_field(
                    name=f"{timestamp} - {action['user']}",
                    value=f"**Action:** {action['action']}\n"
                          f"**Details:** {action['details'][:100]}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error viewing emergency log: {str(e)}")

    @emergency.command(name="reboot_vps")
    async def emergency_reboot_vps(self, ctx):
        """Emergency VPS reboot - LAST RESORT."""
        try:
            embed = discord.Embed(
                title="💀 REBOOT ENTIRE VPS?",
                description="**⚠️ THIS WILL REBOOT THE ENTIRE SERVER ⚠️**\n\n"
                           "This is a NUCLEAR OPTION that will:\n"
                           "• Shut down ALL services\n"
                           "• Restart the entire VPS\n"
                           "• Cause 2-5 minutes downtime\n\n"
                           "**Only use if system is completely unresponsive!**\n\n"
                           "Type `CONFIRM REBOOT` to proceed:",
                color=discord.Color.dark_red()
            )
            
            await ctx.send(embed=embed)
            
            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel
            
            try:
                response = await self.bot.wait_for('message', timeout=30, check=check)
                
                if response.content.strip() == "CONFIRM REBOOT":
                    self.log_emergency(ctx.author, "reboot_vps", "NUCLEAR OPTION - Full VPS reboot")
                    
                    final_warning = discord.Embed(
                        title="💀 REBOOTING VPS IN 10 SECONDS",
                        description="**LAST CHANCE TO CANCEL**\n\n"
                                   "The VPS will reboot in 10 seconds!\n"
                                   "Type `CANCEL` to abort",
                        color=discord.Color.dark_red()
                    )
                    
                    message = await ctx.send(embed=final_warning)
                    
                    # 10 second countdown with cancel option
                    for i in range(10, 0, -1):
                        try:
                            cancel_check = await self.bot.wait_for('message', timeout=1, check=check)
                            if cancel_check.content.strip().upper() == "CANCEL":
                                await ctx.send("❌ VPS REBOOT CANCELLED")
                                return
                        except asyncio.TimeoutError:
                            pass
                        
                        if i > 1:
                            countdown_embed = discord.Embed(
                                title=f"💀 REBOOTING VPS IN {i-1} SECONDS",
                                description="Type `CANCEL` to abort",
                                color=discord.Color.dark_red()
                            )
                            await message.edit(embed=countdown_embed)
                    
                    # Execute reboot
                    await ctx.send("💀 **REBOOTING VPS NOW - GOODBYE**")
                    subprocess.Popen(['sudo', 'reboot'], preexec_fn=os.setsid)
                    
                else:
                    await ctx.send("❌ Incorrect confirmation. VPS reboot cancelled.")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ VPS reboot confirmation timed out. Cancelled for safety.")
                
        except Exception as e:
            await ctx.send(f"❌ Error in VPS reboot: {str(e)}")

async def setup(bot):
    """Set up the Emergency Controls cog."""
    await bot.add_cog(EmergencyControlsCog(bot))
    logger.info("Emergency Controls cog loaded successfully") 