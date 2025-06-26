"""
Enhanced Health Monitoring System for NewsBot
Provides comprehensive system health tracking and alerting.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import discord

from src.utils.debug_logger import debug_logger, debug_context, performance_monitor
from src.utils.base_logger import base_logger as logger
from src.core.unified_config import unified_config as config
from src.cache.json_cache import JSONCache


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    duration_ms: float


@dataclass
class SystemHealth:
    """Overall system health status."""
    overall_status: HealthStatus
    checks: List[HealthCheck]
    last_updated: datetime
    uptime_seconds: float


class HealthMonitor:
    """Enhanced health monitoring system."""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.last_health_check = None
        self.health_history = []
        self.max_history = 100
        
        # Performance tracking
        self.performance_metrics = {
            'api_calls': {'openai': 0, 'discord': 0, 'telegram': 0},
            'errors': {'openai': 0, 'discord': 0, 'telegram': 0, 'general': 0},
            'posts_successful': 0,
            'posts_failed': 0,
            'translations_successful': 0,
            'translations_failed': 0
        }
        
    @debug_context("Health Check")
    async def run_full_health_check(self) -> SystemHealth:
        """Run a comprehensive health check of all systems."""
        debug_logger.info("Starting comprehensive health check")
        
        checks = []
        
        # Define all health checks
        health_checks = [
            self._check_discord_connection,
            self._check_telegram_connection,
            self._check_openai_api,
            self._check_database_connection,
            self._check_memory_usage,
            self._check_disk_space,
            self._check_recent_errors,
            self._check_posting_success_rate,
            self._check_translation_success_rate
        ]
        
        # Run all checks
        for check_func in health_checks:
            try:
                check_result = await check_func()
                checks.append(check_result)
            except Exception as e:
                debug_logger.error(f"Health check {check_func.__name__} failed", error=e)
                checks.append(HealthCheck(
                    name=check_func.__name__,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                    details={'error': str(e)},
                    timestamp=datetime.now(),
                    duration_ms=0
                ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(checks)
        
        # Create system health object
        system_health = SystemHealth(
            overall_status=overall_status,
            checks=checks,
            last_updated=datetime.now(),
            uptime_seconds=time.time() - self.start_time
        )
        
        # Store in history
        self.last_health_check = system_health
        self.health_history.append(system_health)
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)
        
        debug_logger.info("Health check completed", 
                         overall_status=overall_status.value,
                         total_checks=len(checks),
                         healthy_checks=len([c for c in checks if c.status == HealthStatus.HEALTHY]))
        
        return system_health
    
    @performance_monitor("Discord Connection Check")
    async def _check_discord_connection(self) -> HealthCheck:
        """Check Discord bot connection status."""
        start_time = time.time()
        
        try:
            if not self.bot or not self.bot.is_ready():
                return HealthCheck(
                    name="Discord Connection",
                    status=HealthStatus.CRITICAL,
                    message="Bot is not connected to Discord",
                    details={'connected': False},
                    timestamp=datetime.now(),
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Test guild access
            guild_id = config.get("discord.guild_id")
            guild = self.bot.get_guild(guild_id)
            
            if not guild:
                return HealthCheck(
                    name="Discord Connection",
                    status=HealthStatus.CRITICAL,
                    message=f"Cannot access guild {guild_id}",
                    details={'guild_id': guild_id, 'accessible': False},
                    timestamp=datetime.now(),
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Test channel access
            news_channel_id = config.get("discord.channels.news") or config.get("channels.news")
            news_channel = guild.get_channel(news_channel_id)
            
            status = HealthStatus.HEALTHY if news_channel else HealthStatus.WARNING
            message = "Discord connection healthy" if news_channel else "News channel not accessible"
            
            return HealthCheck(
                name="Discord Connection",
                status=status,
                message=message,
                details={
                    'connected': True,
                    'guild_name': guild.name,
                    'guild_members': guild.member_count,
                    'news_channel_accessible': news_channel is not None,
                    'latency_ms': round(self.bot.latency * 1000, 2)
                },
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="Discord Connection",
                status=HealthStatus.CRITICAL,
                message=f"Discord connection check failed: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    @performance_monitor("OpenAI API Check")
    async def _check_openai_api(self) -> HealthCheck:
        """Check OpenAI API connectivity and key validity."""
        start_time = time.time()
        
        try:
            import openai
            api_key = config.get("openai.api_key")
            
            if not api_key:
                return HealthCheck(
                    name="OpenAI API",
                    status=HealthStatus.CRITICAL,
                    message="OpenAI API key not configured",
                    details={'api_key_configured': False},
                    timestamp=datetime.now(),
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Test API with a simple request
            client = openai.OpenAI(api_key=api_key)
            
            # Use a very small test request to minimize costs
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
            )
            
            return HealthCheck(
                name="OpenAI API",
                status=HealthStatus.HEALTHY,
                message="OpenAI API accessible",
                details={
                    'api_key_configured': True,
                    'api_accessible': True,
                    'model_used': 'gpt-3.5-turbo',
                    'successful_calls': self.performance_metrics['api_calls']['openai'],
                    'failed_calls': self.performance_metrics['errors']['openai']
                },
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            error_message = str(e)
            status = HealthStatus.WARNING if "rate limit" in error_message.lower() else HealthStatus.CRITICAL
            
            return HealthCheck(
                name="OpenAI API",
                status=status,
                message=f"OpenAI API check failed: {error_message}",
                details={
                    'api_key_configured': bool(config.get("openai.api_key")),
                    'error': error_message,
                    'successful_calls': self.performance_metrics['api_calls']['openai'],
                    'failed_calls': self.performance_metrics['errors']['openai']
                },
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    @performance_monitor("Telegram Connection Check")
    async def _check_telegram_connection(self) -> HealthCheck:
        """Check Telegram client status."""
        start_time = time.time()
        
        try:
            # Get telegram client from bot instance
            telegram_client = getattr(self.bot, 'telegram_client', None)
            
            if telegram_client is None:
                return HealthCheck(
                    name="Telegram Connection",
                    status=HealthStatus.WARNING,
                    message="Telegram client not initialized",
                    details={'client_available': False, 'reason': 'not_initialized'},
                    timestamp=datetime.now(),
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Check if telegram client is connected
            is_connected = False
            auth_failed = getattr(self.bot, 'telegram_auth_failed', True)
            
            try:
                # Try to check if the client is connected
                if hasattr(telegram_client, 'is_connected'):
                    is_connected = await telegram_client.is_connected()
                elif hasattr(telegram_client, '_client'):
                    # Check underlying telethon client
                    client = telegram_client._client
                    if hasattr(client, 'is_connected'):
                        is_connected = client.is_connected()
                elif hasattr(telegram_client, 'connected'):
                    is_connected = telegram_client.connected
                else:
                    # Fallback: assume connected if not auth failed
                    is_connected = not auth_failed
                    
            except Exception as e:
                logger.debug(f"Error checking telegram connection: {e}")
                is_connected = False
            
            # Determine status based on connection and auth
            if auth_failed:
                status = HealthStatus.CRITICAL
                message = "Telegram authentication failed"
                details = {
                    'connected': False,
                    'authenticated': False,
                    'auth_failed': True
                }
            elif is_connected:
                status = HealthStatus.HEALTHY
                message = "Telegram client connected and authenticated"
                details = {
                    'connected': True,
                    'authenticated': True,
                    'auth_failed': False
                }
            else:
                status = HealthStatus.WARNING
                message = "Telegram client not connected"
                details = {
                    'connected': False,
                    'authenticated': not auth_failed,
                    'auth_failed': auth_failed
                }
            
            return HealthCheck(
                name="Telegram Connection",
                status=status,
                message=message,
                details=details,
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="Telegram Connection",
                status=HealthStatus.CRITICAL,
                message=f"Telegram connection check failed: {str(e)}",
                details={'error': str(e), 'client_available': False},
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    @performance_monitor("Database Connection Check")
    async def _check_database_connection(self) -> HealthCheck:
        """Check database/cache connectivity."""
        start_time = time.time()
        
        try:
            # Test JSON cache access
            cache = JSONCache()
            
            # Simple read test
            test_data = await cache.get("automation_config")
            
            return HealthCheck(
                name="Database/Cache",
                status=HealthStatus.HEALTHY,
                message="Cache system accessible",
                details={
                    'json_cache_accessible': True,
                    'automation_config_loaded': test_data is not None
                },
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="Database/Cache",
                status=HealthStatus.CRITICAL,
                message=f"Cache system check failed: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_memory_usage(self) -> HealthCheck:
        """Check system memory usage."""
        start_time = time.time()
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            status = HealthStatus.HEALTHY
            if memory.percent > 90:
                status = HealthStatus.CRITICAL
            elif memory.percent > 75:
                status = HealthStatus.WARNING
            
            return HealthCheck(
                name="Memory Usage",
                status=status,
                message=f"Memory usage: {memory.percent:.1f}%",
                details={
                    'percent_used': memory.percent,
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2)
                },
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except ImportError:
            return HealthCheck(
                name="Memory Usage",
                status=HealthStatus.UNKNOWN,
                message="psutil not available for memory monitoring",
                details={'psutil_available': False},
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return HealthCheck(
                name="Memory Usage",
                status=HealthStatus.WARNING,
                message=f"Memory check failed: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_disk_space(self) -> HealthCheck:
        """Check available disk space."""
        start_time = time.time()
        
        try:
            import psutil
            disk = psutil.disk_usage('/')
            
            status = HealthStatus.HEALTHY
            percent_used = (disk.used / disk.total) * 100
            
            if percent_used > 95:
                status = HealthStatus.CRITICAL
            elif percent_used > 85:
                status = HealthStatus.WARNING
            
            return HealthCheck(
                name="Disk Space",
                status=status,
                message=f"Disk usage: {percent_used:.1f}%",
                details={
                    'percent_used': round(percent_used, 2),
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'used_gb': round(disk.used / (1024**3), 2)
                },
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except ImportError:
            return HealthCheck(
                name="Disk Space",
                status=HealthStatus.UNKNOWN,
                message="psutil not available for disk monitoring",
                details={'psutil_available': False},
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return HealthCheck(
                name="Disk Space",
                status=HealthStatus.WARNING,
                message=f"Disk check failed: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_recent_errors(self) -> HealthCheck:
        """Check for recent error patterns."""
        start_time = time.time()
        
        # Get error counts from last hour
        recent_errors = sum(self.performance_metrics['errors'].values())
        
        status = HealthStatus.HEALTHY
        if recent_errors > 10:
            status = HealthStatus.CRITICAL
        elif recent_errors > 5:
            status = HealthStatus.WARNING
        
        return HealthCheck(
            name="Recent Errors",
            status=status,
            message=f"Recent errors: {recent_errors}",
            details=self.performance_metrics['errors'],
            timestamp=datetime.now(),
            duration_ms=(time.time() - start_time) * 1000
        )
    
    async def _check_posting_success_rate(self) -> HealthCheck:
        """Check posting success rate."""
        start_time = time.time()
        
        successful = self.performance_metrics['posts_successful']
        failed = self.performance_metrics['posts_failed']
        total = successful + failed
        
        if total == 0:
            success_rate = 100.0
            status = HealthStatus.HEALTHY
        else:
            success_rate = (successful / total) * 100
            
            if success_rate < 70:
                status = HealthStatus.CRITICAL
            elif success_rate < 90:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
        
        return HealthCheck(
            name="Posting Success Rate",
            status=status,
            message=f"Success rate: {success_rate:.1f}% ({successful}/{total})",
            details={
                'successful_posts': successful,
                'failed_posts': failed,
                'total_posts': total,
                'success_rate_percent': round(success_rate, 2)
            },
            timestamp=datetime.now(),
            duration_ms=(time.time() - start_time) * 1000
        )
    
    async def _check_translation_success_rate(self) -> HealthCheck:
        """Check translation success rate."""
        start_time = time.time()
        
        successful = self.performance_metrics['translations_successful']
        failed = self.performance_metrics['translations_failed']
        total = successful + failed
        
        if total == 0:
            success_rate = 100.0
            status = HealthStatus.HEALTHY
        else:
            success_rate = (successful / total) * 100
            
            if success_rate < 80:
                status = HealthStatus.CRITICAL
            elif success_rate < 95:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
        
        return HealthCheck(
            name="Translation Success Rate",
            status=status,
            message=f"Success rate: {success_rate:.1f}% ({successful}/{total})",
            details={
                'successful_translations': successful,
                'failed_translations': failed,
                'total_translations': total,
                'success_rate_percent': round(success_rate, 2)
            },
            timestamp=datetime.now(),
            duration_ms=(time.time() - start_time) * 1000
        )
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall system health from individual checks."""
        if any(check.status == HealthStatus.CRITICAL for check in checks):
            return HealthStatus.CRITICAL
        elif any(check.status == HealthStatus.WARNING for check in checks):
            return HealthStatus.WARNING
        elif all(check.status == HealthStatus.HEALTHY for check in checks):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def record_api_call(self, service: str, success: bool = True):
        """Record an API call for monitoring."""
        if success:
            self.performance_metrics['api_calls'][service] += 1
        else:
            self.performance_metrics['errors'][service] += 1
    
    def record_post_attempt(self, success: bool = True):
        """Record a post attempt for monitoring."""
        if success:
            self.performance_metrics['posts_successful'] += 1
        else:
            self.performance_metrics['posts_failed'] += 1
    
    def record_translation_attempt(self, success: bool = True):
        """Record a translation attempt."""
        if success:
            self.performance_metrics['translations_successful'] += 1
        else:
            self.performance_metrics['translations_failed'] += 1
    
    async def get_health_score(self) -> int:
        """Calculate and return a health score from 0-100 based on recent health checks."""
        try:
            if not self.last_health_check:
                # No health check available, return moderate score
                return 75
            
            # Count healthy vs total checks
            healthy_checks = len([c for c in self.last_health_check.checks if c.status == HealthStatus.HEALTHY])
            total_checks = len(self.last_health_check.checks)
            
            if total_checks == 0:
                return 75
            
            # Base score from health check ratio
            health_ratio = healthy_checks / total_checks
            base_score = int(health_ratio * 100)
            
            # Apply modifiers for critical systems
            critical_systems = ['Discord Connection', 'OpenAI API', 'Database Connection']
            critical_penalties = 0
            
            for check in self.last_health_check.checks:
                if check.name in critical_systems and check.status != HealthStatus.HEALTHY:
                    if check.status == HealthStatus.CRITICAL:
                        critical_penalties += 25
                    elif check.status == HealthStatus.WARNING:
                        critical_penalties += 10
            
            # Calculate final score
            final_score = max(0, min(100, base_score - critical_penalties))
            
            return final_score
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return 50  # Return moderate score on error
    
    async def create_health_embed(self, health: SystemHealth) -> discord.Embed:
        """Create a Discord embed for health status."""
        # Status colors
        color_map = {
            HealthStatus.HEALTHY: 0x00ff00,
            HealthStatus.WARNING: 0xffff00,
            HealthStatus.CRITICAL: 0xff0000,
            HealthStatus.UNKNOWN: 0x808080
        }
        
        # Status emojis
        emoji_map = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️",
            HealthStatus.CRITICAL: "❌",
            HealthStatus.UNKNOWN: "❓"
        }
        
        embed = discord.Embed(
            title=f"{emoji_map[health.overall_status]} System Health Status",
            description=f"Overall Status: **{health.overall_status.value.title()}**",
            color=color_map[health.overall_status],
            timestamp=health.last_updated
        )
        
        # Add uptime
        uptime_str = str(timedelta(seconds=int(health.uptime_seconds)))
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        
        # Add check summary
        healthy_count = len([c for c in health.checks if c.status == HealthStatus.HEALTHY])
        total_checks = len(health.checks)
        embed.add_field(name="Health Checks", value=f"{healthy_count}/{total_checks} Passing", inline=True)
        
        # Add individual check results (top 10 most important)
        important_checks = sorted(health.checks, key=lambda x: (
            0 if x.status == HealthStatus.CRITICAL else
            1 if x.status == HealthStatus.WARNING else
            2 if x.status == HealthStatus.HEALTHY else 3
        ))[:10]
        
        for check in important_checks:
            status_emoji = emoji_map[check.status]
            embed.add_field(
                name=f"{status_emoji} {check.name}",
                value=check.message,
                inline=True
            )
        
        embed.set_footer(text="Health check completed")
        return embed


# Global health monitor instance (will be initialized with bot)
health_monitor: Optional[HealthMonitor] = None


def initialize_health_monitor(bot):
    """Initialize the global health monitor with bot instance."""
    global health_monitor
    health_monitor = HealthMonitor(bot)
    return health_monitor 