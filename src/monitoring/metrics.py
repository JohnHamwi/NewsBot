# =============================================================================
# NewsBot Metrics Module
# =============================================================================
# This module provides Prometheus metrics collection and monitoring functionality
# optimized for low-memory environments with essential metrics tracking
# and comprehensive system resource monitoring.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import os
from datetime import datetime
from typing import Any, Dict

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import psutil
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# =============================================================================
# Local Application Imports
# =============================================================================
from src.utils.base_logger import base_logger as logger


# =============================================================================
# Metrics Manager Main Class
# =============================================================================
class MetricsManager:
    """
    Manages Prometheus metrics collection and exposure.

    Features:
    - Command execution metrics
    - System resource metrics
    - Error tracking
    - Performance monitoring
    - Custom metrics support
    """

    def __init__(self, port: int = 8000):
        """
        Initialize metrics manager.

        Args:
            port (int): Port to expose metrics on
        """
        self.port = port
        self._server_started = False
        self._collection_started = False

        # Reduced number of buckets for histograms
        self.command_latency = Histogram(
            "newsbot_command_latency_seconds",
            "Command execution time",
            ["command_name"],
            buckets=(0.5, 1.0, 2.0),  # Fewer buckets
        )

        # Essential metrics only
        self.error_counter = Counter(
            "newsbot_errors_total", "Total errors encountered", ["error_type"]
        )

        self.memory_usage = Gauge(
            "newsbot_memory_usage_bytes", "Current memory usage in bytes"
        )

        self.message_counter = Counter(
            "newsbot_messages_total", "Total messages processed", ["source"]
        )

        # Dynamic metrics for bot status
        self.bot_latency = Gauge("newsbot_latency_ms", "Bot latency in milliseconds")
        self.guild_count = Gauge("newsbot_guild_count", "Number of guilds")
        self.user_count = Gauge("newsbot_user_count", "Number of users")
        self.cpu_usage = Gauge("newsbot_cpu_usage_percent", "CPU usage percentage")
        self.memory_usage_percent = Gauge(
            "newsbot_memory_usage_percent", "Memory usage percentage"
        )
        self.thread_count = Gauge("newsbot_thread_count", "Number of threads")

    # =========================================================================
    # Server Management Methods
    # =========================================================================
    def start(self) -> None:
        """Start the metrics server."""
        if self._server_started:
            return

        # Try multiple ports if the default is in use
        ports_to_try = [self.port, 8001, 8002, 8003, 8004, 8005]

        for port in ports_to_try:
            try:
                start_http_server(port)
                self._server_started = True
                self.port = port  # Update to the successful port
                logger.info(f"Metrics server started on port {port}")
                return
            except OSError as e:
                if "Address already in use" in str(e):
                    logger.debug(f"Port {port} is in use, trying next port...")
                    continue
                else:
                    logger.error(
                        f"Failed to start metrics server on port {port}: {str(e)}"
                    )
                    raise
            except Exception as e:
                logger.error(f"Failed to start metrics server on port {port}: {str(e)}")
                raise

        # If we get here, all ports failed
        logger.warning(
            "⚠️ Could not start metrics server on any port, continuing without metrics"
        )
        self._server_started = False

    # =========================================================================
    # Collection Management Methods
    # =========================================================================
    def start_collection(self) -> None:
        """Start metrics collection."""
        if self._collection_started:
            return

        try:
            # Start the HTTP server if not already started
            if not self._server_started:
                self.start()

            # Only start collection if server started successfully
            if self._server_started:
                self._collection_started = True
                logger.debug("📊 Metrics collection started")
            else:
                logger.info("📊 Metrics collection disabled (server not available)")

        except Exception as e:
            logger.error(f"Failed to start metrics collection: {str(e)}")
            # Don't raise the exception, just log it and continue without metrics
            logger.info("📊 Continuing without metrics collection")

    def stop_collection(self) -> None:
        """Stop metrics collection."""
        self._collection_started = False
        logger.debug("📊 Metrics collection stopped")

    # =========================================================================
    # Metric Update Methods
    # =========================================================================
    def update_metric(self, metric_name: str, value: float) -> None:
        """
        Update a specific metric by name.

        Args:
            metric_name: Name of the metric to update
            value: New value for the metric
        """
        try:
            if not self._collection_started:
                return

            # Map metric names to Gauge objects
            metric_map = {
                "bot_latency": self.bot_latency,
                "guild_count": self.guild_count,
                "user_count": self.user_count,
                "cpu_usage": self.cpu_usage,
                "memory_usage": self.memory_usage_percent,
                "thread_count": self.thread_count,
            }

            if metric_name in metric_map:
                metric_map[metric_name].set(value)
                logger.debug(f"📊 Updated metric {metric_name}: {value}")
            else:
                logger.warning(f"Unknown metric: {metric_name}")

        except Exception as e:
            logger.error(f"Failed to update metric {metric_name}: {str(e)}")

    # =========================================================================
    # Metric Recording Methods
    # =========================================================================
    def record_command(self, command_name: str, duration: float) -> None:
        """Record command execution metrics."""
        self.command_latency.labels(command_name=command_name).observe(duration)

    def record_error(self, error_type: str) -> None:
        """Record error occurrence."""
        self.error_counter.labels(error_type=error_type).inc()

    def record_message(self, source: str, _: float = None) -> None:
        """Record message count only."""
        self.message_counter.labels(source=source).inc()

    # =========================================================================
    # System Metrics Methods
    # =========================================================================
    def update_system_metrics(self) -> None:
        """Update essential system metrics only."""
        try:
            process = psutil.Process()
            self.memory_usage.set(process.memory_info().rss)

            # Update additional system metrics if collection is active
            if self._collection_started:
                self.cpu_usage.set(psutil.cpu_percent())
                self.memory_usage_percent.set(process.memory_percent())
                self.thread_count.set(process.num_threads())

        except Exception as e:
            logger.error(f"Failed to update system metrics: {str(e)}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get minimal metrics summary."""
        process = psutil.Process()
        return {
            "memory_usage_mb": process.memory_info().rss / 1024 / 1024,
            "errors_total": self.error_counter._value.sum(),
            "collection_active": self._collection_started,
            "server_running": self._server_started,
        }
