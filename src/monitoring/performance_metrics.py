"""
Performance Metrics Service for Syrian NewsBot

Advanced performance monitoring and metrics collection system.

Author: حَـــــنَّـــــا
Version: 3.0.0
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import psutil

from src.utils.base_logger import base_logger as logger


class PerformanceMetrics:
    """Comprehensive performance metrics collection and analysis system."""

    def __init__(self, bot: Any, retention_hours: int = 24) -> None:
        """Initialize performance metrics system."""
        self.bot = bot
        self.retention_hours = retention_hours
        self.start_time = datetime.now(timezone.utc)

        # Metrics storage
        self.system_metrics: deque = deque(maxlen=retention_hours * 60)
        self.command_metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_executions": 0,
                "total_duration": 0.0,
                "error_count": 0,
                "last_execution": None,
                "avg_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "recent_executions": deque(maxlen=100),
            }
        )

        # Error tracking
        self.error_metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "last_occurrence": None,
                "recent_errors": deque(maxlen=50),
            }
        )

        # Auto-posting metrics
        self.auto_post_metrics = {
            "total_posts": 0,
            "successful_posts": 0,
            "failed_posts": 0,
            "avg_post_duration": 0.0,
            "last_post_time": None,
            "recent_posts": deque(maxlen=100),
        }

        # Performance thresholds
        self.thresholds = {
            "cpu_warning": 80.0,
            "cpu_critical": 95.0,
            "memory_warning": 80.0,
            "memory_critical": 95.0,
            "latency_warning": 500.0,
            "latency_critical": 1000.0,
        }

        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False

        logger.info("📊 Performance metrics system initialized")

    async def start_monitoring(self) -> None:
        """Start the performance monitoring task."""
        if self._is_monitoring:
            return

        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🔄 Performance monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the performance monitoring task."""
        self._is_monitoring = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Performance monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._is_monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(60)

    async def _collect_system_metrics(self) -> None:
        """Collect current system metrics."""
        try:
            timestamp = datetime.now(timezone.utc)

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            latency = self.bot.latency * 1000 if hasattr(self.bot, "latency") else 0
            guilds = len(self.bot.guilds) if hasattr(self.bot, "guilds") else 0

            metrics = {
                "timestamp": timestamp,
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_mb": memory.used // (1024 * 1024),
                    "disk_percent": disk.percent,
                },
                "bot": {
                    "latency_ms": latency,
                    "guilds": guilds,
                    "connected": (
                        self.bot.is_ready() if hasattr(self.bot, "is_ready") else False
                    ),
                },
            }

            self.system_metrics.append(metrics)
            await self._check_thresholds(metrics)

        except Exception as e:
            logger.error(f"❌ Error collecting system metrics: {e}")

    async def _check_thresholds(self, metrics: Dict[str, Any]) -> None:
        """Check if metrics exceed thresholds."""
        system = metrics["system"]
        bot = metrics["bot"]

        if system["cpu_percent"] >= self.thresholds["cpu_critical"]:
            logger.warning(f"🚨 CRITICAL: CPU usage {system['cpu_percent']:.1f}%")
        elif system["cpu_percent"] >= self.thresholds["cpu_warning"]:
            logger.warning(f"⚠️ WARNING: CPU usage {system['cpu_percent']:.1f}%")

        if system["memory_percent"] >= self.thresholds["memory_critical"]:
            logger.warning(f"🚨 CRITICAL: Memory usage {system['memory_percent']:.1f}%")
        elif system["memory_percent"] >= self.thresholds["memory_warning"]:
            logger.warning(f"⚠️ WARNING: Memory usage {system['memory_percent']:.1f}%")

        if bot["latency_ms"] >= self.thresholds["latency_critical"]:
            logger.warning(f"🚨 CRITICAL: Discord latency {bot['latency_ms']:.1f}ms")
        elif bot["latency_ms"] >= self.thresholds["latency_warning"]:
            logger.warning(f"⚠️ WARNING: Discord latency {bot['latency_ms']:.1f}ms")

    def record_command_execution(
        self,
        command_name: str,
        duration: float,
        success: bool = True,
        user_id: Optional[int] = None,
    ) -> None:
        """Record a command execution."""
        timestamp = datetime.now(timezone.utc)
        metrics = self.command_metrics[command_name]

        metrics["total_executions"] += 1
        metrics["last_execution"] = timestamp

        if success:
            metrics["total_duration"] += duration
            metrics["min_duration"] = min(metrics["min_duration"], duration)
            metrics["max_duration"] = max(metrics["max_duration"], duration)
            metrics["avg_duration"] = metrics["total_duration"] / (
                metrics["total_executions"] - metrics["error_count"]
            )
        else:
            metrics["error_count"] += 1

        execution_record = {
            "timestamp": timestamp,
            "duration": duration,
            "success": success,
            "user_id": user_id,
        }
        metrics["recent_executions"].append(execution_record)

    def record_error(
        self, error_type: str, error_message: str, context: str = ""
    ) -> None:
        """Record an error occurrence."""
        timestamp = datetime.now(timezone.utc)
        metrics = self.error_metrics[error_type]

        metrics["count"] += 1
        metrics["last_occurrence"] = timestamp

        error_record = {
            "timestamp": timestamp,
            "message": error_message,
            "context": context,
        }
        metrics["recent_errors"].append(error_record)

    def record_auto_post(
        self, success: bool, duration: float, posts_count: int = 1
    ) -> None:
        """Record an auto-posting operation."""
        timestamp = datetime.now(timezone.utc)

        self.auto_post_metrics["total_posts"] += posts_count
        self.auto_post_metrics["last_post_time"] = timestamp

        if success:
            self.auto_post_metrics["successful_posts"] += posts_count
        else:
            self.auto_post_metrics["failed_posts"] += posts_count

        if success and posts_count > 0:
            total_successful = self.auto_post_metrics["successful_posts"]
            current_avg = self.auto_post_metrics["avg_post_duration"]
            self.auto_post_metrics["avg_post_duration"] = (
                current_avg * (total_successful - posts_count) + duration
            ) / total_successful

        post_record = {
            "timestamp": timestamp,
            "success": success,
            "duration": duration,
            "posts_count": posts_count,
        }
        self.auto_post_metrics["recent_posts"].append(post_record)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        current_time = datetime.now(timezone.utc)
        uptime = current_time - self.start_time

        recent_metrics = self._get_recent_system_metrics(hours=1)

        return {
            "timestamp": current_time.isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime).split(".")[0],
            "system_performance": self._get_system_performance_summary(recent_metrics),
            "command_performance": self._get_command_performance_summary(),
            "error_summary": self._get_error_summary(),
            "auto_posting_summary": self._get_auto_posting_summary(),
            "health_score": self._calculate_health_score(),
        }

    def _get_recent_system_metrics(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent system metrics."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            metric
            for metric in self.system_metrics
            if metric["timestamp"] >= cutoff_time
        ]

    def _get_system_performance_summary(
        self, recent_metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get system performance summary."""
        if not recent_metrics:
            return {"error": "No recent metrics available"}

        cpu_values = [m["system"]["cpu_percent"] for m in recent_metrics]
        memory_values = [m["system"]["memory_percent"] for m in recent_metrics]
        latency_values = [m["bot"]["latency_ms"] for m in recent_metrics]

        return {
            "cpu": {
                "current": cpu_values[-1] if cpu_values else 0,
                "average": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "peak": max(cpu_values) if cpu_values else 0,
            },
            "memory": {
                "current": memory_values[-1] if memory_values else 0,
                "average": (
                    sum(memory_values) / len(memory_values) if memory_values else 0
                ),
                "peak": max(memory_values) if memory_values else 0,
            },
            "latency": {
                "current": latency_values[-1] if latency_values else 0,
                "average": (
                    sum(latency_values) / len(latency_values) if latency_values else 0
                ),
                "peak": max(latency_values) if latency_values else 0,
            },
        }

    def _get_command_performance_summary(self) -> Dict[str, Any]:
        """Get command performance summary."""
        if not self.command_metrics:
            return {"total_commands": 0, "commands": {}}

        total_executions = sum(
            cmd["total_executions"] for cmd in self.command_metrics.values()
        )
        total_errors = sum(cmd["error_count"] for cmd in self.command_metrics.values())

        top_commands = sorted(
            self.command_metrics.items(),
            key=lambda x: x[1]["total_executions"],
            reverse=True,
        )[:5]

        return {
            "total_executions": total_executions,
            "total_errors": total_errors,
            "error_rate": (
                (total_errors / total_executions * 100) if total_executions > 0 else 0
            ),
            "unique_commands": len(self.command_metrics),
            "top_commands": [
                {
                    "name": name,
                    "executions": metrics["total_executions"],
                    "avg_duration": metrics["avg_duration"],
                    "error_rate": (
                        (metrics["error_count"] / metrics["total_executions"] * 100)
                        if metrics["total_executions"] > 0
                        else 0
                    ),
                }
                for name, metrics in top_commands
            ],
        }

    def _get_error_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        if not self.error_metrics:
            return {"total_errors": 0, "error_types": {}}

        total_errors = sum(error["count"] for error in self.error_metrics.values())

        return {
            "total_errors": total_errors,
            "error_types": len(self.error_metrics),
            "top_errors": [
                {
                    "type": error_type,
                    "count": metrics["count"],
                    "last_occurrence": (
                        metrics["last_occurrence"].isoformat()
                        if metrics["last_occurrence"]
                        else None
                    ),
                }
                for error_type, metrics in sorted(
                    self.error_metrics.items(),
                    key=lambda x: x[1]["count"],
                    reverse=True,
                )[:5]
            ],
        }

    def _get_auto_posting_summary(self) -> Dict[str, Any]:
        """Get auto-posting summary."""
        metrics = self.auto_post_metrics

        success_rate = 0
        if metrics["total_posts"] > 0:
            success_rate = (metrics["successful_posts"] / metrics["total_posts"]) * 100

        return {
            "total_posts": metrics["total_posts"],
            "successful_posts": metrics["successful_posts"],
            "failed_posts": metrics["failed_posts"],
            "success_rate": success_rate,
            "avg_duration": metrics["avg_post_duration"],
            "last_post": (
                metrics["last_post_time"].isoformat()
                if metrics["last_post_time"]
                else None
            ),
        }

    def _calculate_health_score(self) -> Dict[str, Any]:
        """Calculate overall health score (0-100)."""
        scores = []

        # System health
        recent_metrics = self._get_recent_system_metrics(hours=1)
        if recent_metrics:
            latest = recent_metrics[-1]
            cpu_score = max(0, 100 - latest["system"]["cpu_percent"])
            memory_score = max(0, 100 - latest["system"]["memory_percent"])
            latency_score = max(0, 100 - (latest["bot"]["latency_ms"] / 10))
            system_score = (cpu_score + memory_score + latency_score) / 3
            scores.append(("system", system_score, 0.4))

        # Command performance
        if self.command_metrics:
            total_executions = sum(
                cmd["total_executions"] for cmd in self.command_metrics.values()
            )
            total_errors = sum(
                cmd["error_count"] for cmd in self.command_metrics.values()
            )
            error_rate = (
                (total_errors / total_executions * 100) if total_executions > 0 else 0
            )
            command_score = max(0, 100 - (error_rate * 10))
            scores.append(("commands", command_score, 0.3))

        # Auto-posting performance
        auto_metrics = self.auto_post_metrics
        if auto_metrics["total_posts"] > 0:
            success_rate = (
                auto_metrics["successful_posts"] / auto_metrics["total_posts"]
            ) * 100
            scores.append(("auto_posting", success_rate, 0.3))

        if scores:
            weighted_score = sum(score * weight for _, score, weight in scores)
            total_weight = sum(weight for _, _, weight in scores)
            overall_score = weighted_score / total_weight if total_weight > 0 else 0
        else:
            overall_score = 0

        return {
            "overall_score": round(overall_score, 1),
            "components": {name: round(score, 1) for name, score, _ in scores},
            "status": self._get_health_status(overall_score),
        }

    def _get_health_status(self, score: float) -> str:
        """Get health status based on score."""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "fair"
        elif score >= 40:
            return "poor"
        else:
            return "critical"

    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        lines = []
        timestamp = int(time.time() * 1000)

        # System metrics
        if self.system_metrics:
            latest = self.system_metrics[-1]
            system = latest["system"]
            bot = latest["bot"]

            lines.extend(
                [
                    f"# HELP newsbot_cpu_percent Current CPU usage percentage",
                    f"# TYPE newsbot_cpu_percent gauge",
                    f"newsbot_cpu_percent {system['cpu_percent']} {timestamp}",
                    f"# HELP newsbot_memory_percent Current memory usage percentage",
                    f"# TYPE newsbot_memory_percent gauge",
                    f"newsbot_memory_percent {system['memory_percent']} {timestamp}",
                    f"# HELP newsbot_latency_ms Current Discord API latency",
                    f"# TYPE newsbot_latency_ms gauge",
                    f"newsbot_latency_ms {bot['latency_ms']} {timestamp}",
                ]
            )

        # Command metrics
        for command_name, metrics in self.command_metrics.items():
            lines.extend(
                [
                    f"# HELP newsbot_command_executions_total Total command executions",
                    f"# TYPE newsbot_command_executions_total counter",
                    f"newsbot_command_executions_total{{command=\"{command_name}\"}} {metrics['total_executions']} {timestamp}",
                    f"# HELP newsbot_command_errors_total Total command errors",
                    f"# TYPE newsbot_command_errors_total counter",
                    f"newsbot_command_errors_total{{command=\"{command_name}\"}} {metrics['error_count']} {timestamp}",
                ]
            )

        return "\n".join(lines) + "\n"
