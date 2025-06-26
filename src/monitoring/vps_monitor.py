"""
VPS Production Monitoring System
Advanced monitoring for 24/7 VPS deployment with Discord webhook alerts
"""

import asyncio
import aiohttp
import psutil
import time
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from src.utils.base_logger import base_logger as logger
from src.core.unified_config import unified_config as config


@dataclass
class VPSHealth:
    """VPS health metrics."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_average: List[float]
    network_connections: int
    uptime_hours: float
    bot_process_count: int
    redis_status: bool
    disk_io_read: int
    disk_io_write: int
    network_bytes_sent: int
    network_bytes_recv: int


class VPSMonitor:
    """Production VPS monitoring with Discord alerts."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or config.get("monitoring.discord_webhook")
        self.alert_thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 85.0,
            'memory_warning': 75.0,
            'memory_critical': 90.0,
            'disk_warning': 80.0,
            'disk_critical': 95.0,
            'load_critical': 4.0,
            'uptime_warning': 168  # 7 days - time to restart
        }
        
        self.last_alerts = {}
        self.alert_cooldown = 3600  # 1 hour
        self.metrics_history = []
        self.max_history = 288  # 24 hours at 5-min intervals
        
        # VPS optimization settings
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
        
    async def get_vps_health(self) -> VPSHealth:
        """Get comprehensive VPS health metrics."""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Load average
            load_avg = list(psutil.getloadavg())
            
            # Network
            net_connections = len(psutil.net_connections())
            net_io = psutil.net_io_counters()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime_hours = (time.time() - boot_time) / 3600
            
            # Bot process info
            bot_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline']) 
                           if 'newsbot' in str(p.info.get('cmdline', '')).lower()]
            
            # Redis status
            redis_status = await self._check_redis_status()
            
            return VPSHealth(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                load_average=load_avg,
                network_connections=net_connections,
                uptime_hours=uptime_hours,
                bot_process_count=len(bot_processes),
                redis_status=redis_status,
                disk_io_read=disk_io.read_bytes if disk_io else 0,
                disk_io_write=disk_io.write_bytes if disk_io else 0,
                network_bytes_sent=net_io.bytes_sent if net_io else 0,
                network_bytes_recv=net_io.bytes_recv if net_io else 0
            )
            
        except Exception as e:
            logger.error(f"Failed to get VPS health metrics: {e}")
            raise
    
    async def _check_redis_status(self) -> bool:
        """Check if Redis is running."""
        try:
            result = subprocess.run(['redis-cli', 'ping'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and 'PONG' in result.stdout
        except Exception:
            return False
    
    async def analyze_health(self, health: VPSHealth) -> List[Dict[str, Any]]:
        """Analyze health metrics and generate alerts."""
        alerts = []
        
        # CPU alerts
        if health.cpu_percent >= self.alert_thresholds['cpu_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'cpu',
                'message': f'🔥 Critical CPU usage: {health.cpu_percent:.1f}%',
                'value': health.cpu_percent,
                'threshold': self.alert_thresholds['cpu_critical']
            })
        elif health.cpu_percent >= self.alert_thresholds['cpu_warning']:
            alerts.append({
                'level': 'WARNING',
                'type': 'cpu',
                'message': f'⚠️ High CPU usage: {health.cpu_percent:.1f}%',
                'value': health.cpu_percent,
                'threshold': self.alert_thresholds['cpu_warning']
            })
        
        # Memory alerts
        if health.memory_percent >= self.alert_thresholds['memory_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'memory',
                'message': f'💾 Critical memory usage: {health.memory_percent:.1f}%',
                'value': health.memory_percent,
                'threshold': self.alert_thresholds['memory_critical']
            })
        elif health.memory_percent >= self.alert_thresholds['memory_warning']:
            alerts.append({
                'level': 'WARNING',
                'type': 'memory',
                'message': f'💾 High memory usage: {health.memory_percent:.1f}%',
                'value': health.memory_percent,
                'threshold': self.alert_thresholds['memory_warning']
            })
        
        # Disk space alerts
        if health.disk_percent >= self.alert_thresholds['disk_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'disk',
                'message': f'💿 Critical disk usage: {health.disk_percent:.1f}%',
                'value': health.disk_percent,
                'threshold': self.alert_thresholds['disk_critical']
            })
        elif health.disk_percent >= self.alert_thresholds['disk_warning']:
            alerts.append({
                'level': 'WARNING',
                'type': 'disk',
                'message': f'💿 High disk usage: {health.disk_percent:.1f}%',
                'value': health.disk_percent,
                'threshold': self.alert_thresholds['disk_warning']
            })
        
        # Load average alerts
        if health.load_average[0] >= self.alert_thresholds['load_critical']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'load',
                'message': f'⚡ High system load: {health.load_average[0]:.2f}',
                'value': health.load_average[0],
                'threshold': self.alert_thresholds['load_critical']
            })
        
        # Bot process alerts
        if health.bot_process_count == 0:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'bot_process',
                'message': '🤖 Bot process not found!',
                'value': health.bot_process_count,
                'threshold': 1
            })
        elif health.bot_process_count > 1:
            alerts.append({
                'level': 'WARNING',
                'type': 'bot_process',
                'message': f'🤖 Multiple bot processes running: {health.bot_process_count}',
                'value': health.bot_process_count,
                'threshold': 1
            })
        
        # Redis alerts
        if not health.redis_status:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'redis',
                'message': '🔴 Redis server is down!',
                'value': False,
                'threshold': True
            })
        
        # Uptime alerts (restart recommendation)
        if health.uptime_hours >= self.alert_thresholds['uptime_warning']:
            alerts.append({
                'level': 'INFO',
                'type': 'uptime',
                'message': f'🕐 VPS uptime: {health.uptime_hours:.1f}h - Consider restart for maintenance',
                'value': health.uptime_hours,
                'threshold': self.alert_thresholds['uptime_warning']
            })
        
        return alerts
    
    async def send_discord_alert(self, alerts: List[Dict[str, Any]], health: VPSHealth):
        """Send Discord webhook alert."""
        if not self.webhook_url or not alerts:
            return
        
        # Check alert cooldown
        critical_alerts = [a for a in alerts if a['level'] == 'CRITICAL']
        for alert in critical_alerts:
            alert_key = f"{alert['type']}_{alert['level']}"
            if alert_key in self.last_alerts:
                if time.time() - self.last_alerts[alert_key] < self.alert_cooldown:
                    continue
            self.last_alerts[alert_key] = time.time()
        
        # Build embed
        color = 0xFF0000 if critical_alerts else 0xFFAA00  # Red for critical, orange for warning
        title = "🚨 VPS Critical Alert" if critical_alerts else "⚠️ VPS Warning"
        
        embed = {
            "title": title,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "🖥️ System Status",
                    "value": f"CPU: {health.cpu_percent:.1f}% | Memory: {health.memory_percent:.1f}% | Disk: {health.disk_percent:.1f}%",
                    "inline": False
                },
                {
                    "name": "🤖 Bot Status",
                    "value": f"Processes: {health.bot_process_count} | Redis: {'✅' if health.redis_status else '❌'}",
                    "inline": True
                },
                {
                    "name": "⚡ Load Average",
                    "value": f"{health.load_average[0]:.2f}, {health.load_average[1]:.2f}, {health.load_average[2]:.2f}",
                    "inline": True
                }
            ]
        }
        
        # Add alert details
        alert_text = "\n".join([alert['message'] for alert in alerts[:5]])  # Limit to 5 alerts
        embed["fields"].append({
            "name": "🚨 Alerts",
            "value": alert_text,
            "inline": False
        })
        
        payload = {
            "username": "NewsBot VPS Monitor",
            "embeds": [embed]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info("Discord alert sent successfully")
                    else:
                        logger.error(f"Failed to send Discord alert: {response.status}")
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
    
    async def perform_vps_cleanup(self):
        """Perform VPS maintenance and cleanup."""
        if time.time() - self.last_cleanup < self.cleanup_interval:
            return
        
        logger.info("🧹 Starting VPS cleanup...")
        
        try:
            # Clear system caches
            subprocess.run(['sync'], check=True)
            subprocess.run(['echo', '3'], stdout=open('/proc/sys/vm/drop_caches', 'w'), check=True)
            
            # Rotate logs
            subprocess.run(['logrotate', '-f', '/etc/logrotate.d/newsbot'], check=False)
            
            # Clean temporary files
            subprocess.run(['find', '/tmp', '-type', 'f', '-atime', '+1', '-delete'], check=False)
            
            # Clean old journal logs (keep 7 days)
            subprocess.run(['journalctl', '--vacuum-time=7d'], check=False)
            
            logger.info("✅ VPS cleanup completed")
            
        except Exception as e:
            logger.error(f"VPS cleanup failed: {e}")
        
        self.last_cleanup = time.time()
    
    async def monitoring_loop(self):
        """Main monitoring loop for VPS."""
        logger.info("🔍 Starting VPS monitoring loop...")
        
        while True:
            try:
                # Get health metrics
                health = await self.get_vps_health()
                
                # Store in history
                self.metrics_history.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'health': health.__dict__
                })
                
                # Trim history
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history:]
                
                # Analyze and send alerts
                alerts = await self.analyze_health(health)
                if alerts:
                    await self.send_discord_alert(alerts, health)
                
                # Perform cleanup if needed
                await self.perform_vps_cleanup()
                
                # Log status
                logger.info(f"VPS Status: CPU={health.cpu_percent:.1f}% MEM={health.memory_percent:.1f}% "
                           f"DISK={health.disk_percent:.1f}% LOAD={health.load_average[0]:.2f} "
                           f"BOT_PROCS={health.bot_process_count}")
                
                # Wait 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"VPS monitoring error: {e}")
                await asyncio.sleep(60)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get recent health summary."""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        latest = self.metrics_history[-1]['health']
        
        # Calculate trends
        if len(self.metrics_history) >= 12:  # 1 hour of data
            hour_ago = self.metrics_history[-12]['health']
            cpu_trend = latest['cpu_percent'] - hour_ago['cpu_percent']
            memory_trend = latest['memory_percent'] - hour_ago['memory_percent']
        else:
            cpu_trend = 0
            memory_trend = 0
        
        return {
            "current_status": latest,
            "trends": {
                "cpu_1h": f"{cpu_trend:+.1f}%",
                "memory_1h": f"{memory_trend:+.1f}%"
            },
            "health_score": self._calculate_health_score(VPSHealth(**latest)),
            "last_updated": self.metrics_history[-1]['timestamp']
        }
    
    def _calculate_health_score(self, health: VPSHealth) -> int:
        """Calculate overall health score (0-100)."""
        score = 100
        
        # Deduct points for resource usage
        if health.cpu_percent > 70:
            score -= min((health.cpu_percent - 70) * 2, 40)
        
        if health.memory_percent > 70:
            score -= min((health.memory_percent - 70) * 2, 30)
        
        if health.disk_percent > 80:
            score -= min((health.disk_percent - 80), 20)
        
        if health.load_average[0] > 2.0:
            score -= min((health.load_average[0] - 2.0) * 10, 20)
        
        if health.bot_process_count != 1:
            score -= 15
        
        if not health.redis_status:
            score -= 25
        
        return max(0, int(score))


# Global VPS monitor instance
vps_monitor = None

def initialize_vps_monitor(webhook_url: Optional[str] = None) -> VPSMonitor:
    """Initialize the VPS monitor."""
    global vps_monitor
    vps_monitor = VPSMonitor(webhook_url)
    return vps_monitor

def get_vps_monitor() -> Optional[VPSMonitor]:
    """Get the global VPS monitor instance."""
    return vps_monitor 