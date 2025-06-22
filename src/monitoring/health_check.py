# =============================================================================
# NewsBot Health Check Service Module
# =============================================================================
# Provides comprehensive health monitoring endpoints and system status checks
# for production monitoring and alerting systems. Includes HTTP endpoints for
# health, metrics, readiness, and liveness probes.
# Last updated: 2025-01-16

# =============================================================================
# Future Imports
# =============================================================================
from __future__ import annotations

# =============================================================================
# Standard Library Imports
# =============================================================================
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import psutil
from aiohttp import web

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils.base_logger import base_logger as logger


# =============================================================================
# Health Check Service Main Class
# =============================================================================
class HealthCheckService:
    """
    Comprehensive health check service for monitoring bot status.
    
    Features:
    - HTTP endpoints for health monitoring
    - Kubernetes-style readiness and liveness probes
    - Prometheus-compatible metrics endpoint
    - Detailed system and service status reporting
    - Production-ready monitoring capabilities
    """

    def __init__(self, bot: Any, port: int = 8080) -> None:
        """Initialize health check service."""
        self.bot = bot
        self.port = port
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

        self.start_time = datetime.now(timezone.utc)
        self.last_health_check = datetime.now(timezone.utc)
        self.health_status = "starting"

        self._setup_routes()
        logger.info(f"🏥 Health check service initialized on port {port}")

    # =========================================================================
    # Route Setup Methods
    # =========================================================================
    def _setup_routes(self) -> None:
        """Setup HTTP routes for health check endpoints."""
        self.app.router.add_get("/health", self.health_endpoint)
        self.app.router.add_get("/health/detailed", self.detailed_health_endpoint)
        self.app.router.add_get("/metrics", self.metrics_endpoint)
        self.app.router.add_get("/ready", self.readiness_endpoint)
        self.app.router.add_get("/live", self.liveness_endpoint)

    # =========================================================================
    # Server Lifecycle Methods
    # =========================================================================
    async def start(self) -> None:
        """Start the health check HTTP server."""
        try:
            # Initialize the runner
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            # Create and start the site
            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()

            logger.info(f"🌐 Health check server started on http://0.0.0.0:{self.port}")
            self.health_status = "healthy"

        except Exception as e:
            logger.error(f"❌ Failed to start health check server: {e}")
            self.health_status = "unhealthy"
            
            # Clean up any partial initialization
            try:
                if self.runner:
                    await self.runner.cleanup()
                    self.runner = None
                self.site = None
            except Exception as cleanup_error:
                logger.debug(f"Cleanup during start failure: {cleanup_error}")
            
            raise

    async def stop(self) -> None:
        """Stop the health check HTTP server."""
        try:
            # Stop the site first if it exists and is running
            if self.site:
                try:
                    await self.site.stop()
                    logger.debug("🛑 Health check site stopped")
                except Exception as site_error:
                    # This is expected if the site wasn't properly started or registered
                    logger.debug(f"Health check site stop warning: {site_error}")
            
            # Clean up the runner
            if self.runner:
                try:
                    await self.runner.cleanup()
                    logger.debug("🛑 Health check runner cleaned up")
                except Exception as runner_error:
                    logger.debug(f"Health check runner cleanup warning: {runner_error}")
            
            # Reset state
            self.site = None
            self.runner = None
            
            logger.info("🏥 Health check service stopped")
            
        except Exception as e:
            # Log expected shutdown errors as debug, unexpected ones as error
            error_msg = str(e).lower()
            if "not registered" in error_msg or "site" in error_msg:
                logger.debug(f"Health check shutdown warning: {e}")
            else:
                logger.error(f"❌ Error stopping health check server: {e}")

    # =========================================================================
    # Health Check Endpoints
    # =========================================================================
    async def health_endpoint(self, request: web.Request) -> web.Response:
        """Basic health check endpoint."""
        try:
            health_data = await self._get_basic_health()
            status_code = 200 if health_data["status"] == "healthy" else 503
            return web.json_response(health_data, status=status_code)
        except Exception as e:
            logger.error(f"❌ Health check endpoint error: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def detailed_health_endpoint(self, request: web.Request) -> web.Response:
        """Detailed health check endpoint."""
        try:
            health_data = await self._get_detailed_health()
            status_code = 200 if health_data["overall_status"] == "healthy" else 503
            return web.json_response(health_data, status=status_code)
        except Exception as e:
            logger.error(f"❌ Detailed health check error: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def metrics_endpoint(self, request: web.Request) -> web.Response:
        """Performance metrics endpoint in Prometheus format."""
        try:
            metrics = await self._get_performance_metrics()
            prometheus_metrics = self._format_prometheus_metrics(metrics)

            return web.Response(
                text=prometheus_metrics,
                content_type="text/plain"
            )
        except Exception as e:
            logger.error(f"❌ Metrics endpoint error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    # =========================================================================
    # Kubernetes-Style Probe Endpoints
    # =========================================================================
    async def readiness_endpoint(self, request: web.Request) -> web.Response:
        """Kubernetes-style readiness probe."""
        try:
            is_ready = await self._check_readiness()
            status_code = 200 if is_ready else 503
            status_text = "ready" if is_ready else "not_ready"
            return web.json_response({"status": status_text}, status=status_code)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def liveness_endpoint(self, request: web.Request) -> web.Response:
        """Kubernetes-style liveness probe."""
        try:
            is_alive = await self._check_liveness()
            status_code = 200 if is_alive else 503
            status_text = "alive" if is_alive else "dead"
            return web.json_response({"status": status_text}, status=status_code)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    # =========================================================================
    # Health Data Collection Methods
    # =========================================================================
    async def _get_basic_health(self) -> Dict[str, Any]:
        """Get basic health status."""
        uptime = datetime.now(timezone.utc) - self.start_time

        return {
            "status": self.health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "bot_connected": (
                self.bot.is_ready() if hasattr(self.bot, "is_ready") else False
            ),
            "version": "4.5.0",
        }

    async def _get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information."""
        uptime = datetime.now(timezone.utc) - self.start_time
        services = await self._check_all_services()

        # Determine overall status
        overall_status = "healthy"
        if any(
            service["status"] not in ["healthy", "disabled"]
            for service in services.values()
        ):
            overall_status = "degraded"

        if not (self.bot.is_ready() if hasattr(self.bot, "is_ready") else True):
            overall_status = "unhealthy"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime).split(".")[0],
            "bot_info": {
                "connected": (
                    self.bot.is_ready() if hasattr(self.bot, "is_ready") else False
                ),
                "user": (
                    str(self.bot.user)
                    if hasattr(self.bot, "user") and self.bot.user
                    else None
                ),
                "guilds": len(self.bot.guilds) if hasattr(self.bot, "guilds") else 0,
                "latency_ms": (
                    round(self.bot.latency * 1000, 2)
                    if hasattr(self.bot, "latency")
                    else None
                ),
            },
            "services": services,
            "system": await self._get_system_info(),
            "last_check": self.last_health_check.isoformat(),
        }

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Bot-specific metrics
        bot_metrics = {
            "guilds_count": len(self.bot.guilds) if hasattr(self.bot, "guilds") else 0,
            "latency_ms": (
                round(self.bot.latency * 1000, 2) if hasattr(self.bot, "latency") else 0
            ),
            "uptime_seconds": (
                datetime.now(timezone.utc) - self.start_time
            ).total_seconds(),
        }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used // (1024 * 1024),
                "memory_total_mb": memory.total // (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used // (1024 * 1024 * 1024),
                "disk_total_gb": disk.total // (1024 * 1024 * 1024),
            },
            "bot": bot_metrics,
            "auto_posting": await self._get_auto_post_metrics(),
        }

    async def _check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Check status of all bot services."""
        return {
            "discord": await self._check_discord_service(),
            "telegram": await self._check_telegram_service(),
            "cache": await self._check_cache_service(),
            "background_tasks": await self._check_background_tasks(),
        }

    async def _check_discord_service(self) -> Dict[str, Any]:
        """Check Discord service health."""
        try:
            if not hasattr(self.bot, "is_ready") or not self.bot.is_ready():
                return {
                    "status": "unhealthy",
                    "message": "Discord bot not connected",
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }

            latency = self.bot.latency if hasattr(self.bot, "latency") else 0
            if latency > 1.0:
                return {
                    "status": "degraded",
                    "message": f"High latency: {latency:.2f}s",
                    "latency_ms": round(latency * 1000, 2),
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }

            return {
                "status": "healthy",
                "message": "Discord connection stable",
                "latency_ms": round(latency * 1000, 2),
                "guilds": len(self.bot.guilds) if hasattr(self.bot, "guilds") else 0,
                "last_check": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Discord check failed: {e}",
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

    async def _check_telegram_service(self) -> Dict[str, Any]:
        """Check Telegram service health."""
        try:
            if not hasattr(self.bot, "telegram_client") or not self.bot.telegram_client:
                return {
                    "status": "disabled",
                    "message": "Telegram client not configured",
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }

            return {
                "status": "healthy",
                "message": "Telegram client available",
                "last_check": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Telegram check failed: {e}",
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

    async def _check_cache_service(self) -> Dict[str, Any]:
        """Check cache service health."""
        try:
            if not hasattr(self.bot, "json_cache") or not self.bot.json_cache:
                return {
                    "status": "disabled",
                    "message": "Cache not configured",
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }

            return {
                "status": "healthy",
                "message": "Cache operational",
                "last_check": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Cache check failed: {e}",
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

    async def _check_background_tasks(self) -> Dict[str, Any]:
        """Check background tasks health."""
        try:
            from src.utils.task_manager import task_manager

            if not task_manager:
                return {
                    "status": "disabled",
                    "message": "Task manager not available",
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }

            running_tasks = getattr(task_manager, "running_tasks", {})

            return {
                "status": "healthy",
                "message": f"{len(running_tasks)} background tasks running",
                "running_tasks": list(running_tasks.keys()),
                "last_check": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Background tasks check failed: {e}",
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        try:
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu_cores": cpu_count,
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
            }
        except Exception as e:
            logger.error(f"❌ Error getting system info: {e}")
            return {"error": str(e)}

    async def _get_auto_post_metrics(self) -> Dict[str, Any]:
        """Get auto-posting metrics."""
        try:
            if hasattr(self.bot, "last_post_time") and self.bot.last_post_time:
                last_post_ago = (
                    datetime.now(timezone.utc) - self.bot.last_post_time
                ).total_seconds()
            else:
                last_post_ago = None

            return {
                "interval_minutes": getattr(self.bot, "auto_post_interval", 0),
                "last_post_seconds_ago": last_post_ago,
            }
        except Exception as e:
            logger.error(f"❌ Error getting auto-post metrics: {e}")
            return {"error": str(e)}

    async def _check_readiness(self) -> bool:
        """Check if the bot is ready to serve traffic."""
        try:
            if not hasattr(self.bot, "is_ready") or not self.bot.is_ready():
                return False

            services = await self._check_all_services()
            critical_services = ["discord", "cache"]

            for service_name in critical_services:
                if service_name in services:
                    if services[service_name]["status"] not in ["healthy", "disabled"]:
                        return False

            return True
        except Exception:
            return False

    async def _check_liveness(self) -> bool:
        """Check if the bot is alive and functioning."""
        try:
            self.last_health_check = datetime.now(timezone.utc)

            # Check system resources aren't exhausted
            memory = psutil.virtual_memory()
            if memory.percent > 95:
                return False

            return True
        except Exception:
            return False

    def _format_prometheus_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics in Prometheus format."""
        lines = []
        timestamp = int(time.time() * 1000)

        # System metrics
        if "system" in metrics:
            sys_metrics = metrics["system"]
            lines.extend(
                [
                    f"# HELP newsbot_cpu_percent CPU usage percentage",
                    f"# TYPE newsbot_cpu_percent gauge",
                    f"newsbot_cpu_percent {sys_metrics.get('cpu_percent', 0)} {timestamp}",
                    f"# HELP newsbot_memory_percent Memory usage percentage",
                    f"# TYPE newsbot_memory_percent gauge",
                    f"newsbot_memory_percent {sys_metrics.get('memory_percent', 0)} {timestamp}",
                    f"# HELP newsbot_disk_percent Disk usage percentage",
                    f"# TYPE newsbot_disk_percent gauge",
                    f"newsbot_disk_percent {sys_metrics.get('disk_percent', 0)} {timestamp}",
                ]
            )

        # Bot metrics
        if "bot" in metrics:
            bot_metrics = metrics["bot"]
            lines.extend(
                [
                    f"# HELP newsbot_guilds_total Number of Discord guilds",
                    f"# TYPE newsbot_guilds_total gauge",
                    f"newsbot_guilds_total {bot_metrics.get('guilds_count', 0)} {timestamp}",
                    f"# HELP newsbot_latency_milliseconds Discord API latency",
                    f"# TYPE newsbot_latency_milliseconds gauge",
                    f"newsbot_latency_milliseconds {bot_metrics.get('latency_ms', 0)} {timestamp}",
                    f"# HELP newsbot_uptime_seconds Bot uptime in seconds",
                    f"# TYPE newsbot_uptime_seconds counter",
                    f"newsbot_uptime_seconds {bot_metrics.get('uptime_seconds', 0)} {timestamp}",
                ]
            )

        return "\n".join(lines) + "\n"
