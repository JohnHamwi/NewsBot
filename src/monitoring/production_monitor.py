"""
Production Monitoring System for NewsBot

This module provides comprehensive monitoring capabilities including:
- Performance metrics tracking
- Error rate monitoring  
- Posting interval validation
- Memory and CPU usage tracking
- Alert system for critical issues
"""

import asyncio
import psutil
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class MetricSnapshot:
    """A snapshot of bot metrics at a specific time."""
    timestamp: str
    posting_intervals: List[float]  # Seconds between posts
    memory_usage_mb: float
    cpu_percent: float
    active_channels: int
    successful_posts: int
    failed_posts: int
    error_rate: float
    uptime_hours: float
    last_post_time: Optional[str]
    next_expected_post: Optional[str]

@dataclass
class AlertThresholds:
    """Configuration for monitoring alerts."""
    max_memory_mb: float = 500.0
    max_cpu_percent: float = 80.0
    max_error_rate: float = 0.1  # 10%
    min_posting_interval: float = 2.5 * 60 * 60  # 2.5 hours (should be ~3)
    max_posting_interval: float = 4.0 * 60 * 60  # 4 hours
    max_consecutive_failures: int = 3

class ProductionMonitor:
    """Comprehensive production monitoring for NewsBot."""
    
    def __init__(self, bot_instance, config_path: str = "data/monitoring_config.json"):
        self.bot = bot_instance
        self.config_path = Path(config_path)
        self.metrics_file = Path("data/metrics_history.json")
        self.alerts_file = Path("data/alerts.json")
        
        # Monitoring state
        self.start_time = datetime.now(timezone.utc)
        self.metrics_history: List[Dict] = []
        self.posting_intervals: List[float] = []
        self.consecutive_failures = 0
        self.last_alert_time: Dict[str, datetime] = {}
        
        # Alert configuration
        self.thresholds = AlertThresholds()
        self.load_config()
        
        # Setup logging
        self.setup_monitoring_logger()
        
        self.logger.info("🔍 Production monitoring system initialized")

    def setup_monitoring_logger(self):
        """Setup dedicated monitoring logger."""
        self.logger = logging.getLogger("NewsBot.Monitor")
        
        # Create monitoring log file handler
        log_file = Path("logs/monitoring.log")
        log_file.parent.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s | [%(levelname)s] | %(message)s'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def load_config(self):
        """Load monitoring configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    
                # Update thresholds from config
                for key, value in config.get("alert_thresholds", {}).items():
                    if hasattr(self.thresholds, key):
                        setattr(self.thresholds, key, value)
                        
                self.logger.info(f"✅ Loaded monitoring config from {self.config_path}")
            except Exception as e:
                self.logger.error(f"❌ Failed to load monitoring config: {e}")

    def save_config(self):
        """Save current monitoring configuration."""
        config = {
            "alert_thresholds": asdict(self.thresholds),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        self.config_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Failed to save monitoring config: {e}")

    def record_post_success(self, channel: str):
        """Record a successful post."""
        current_time = datetime.now(timezone.utc)
        
        # Calculate interval if we have a last post time
        if hasattr(self.bot, 'last_post_time') and self.bot.last_post_time:
            if isinstance(self.bot.last_post_time, str):
                last_post = datetime.fromisoformat(self.bot.last_post_time)
            else:
                last_post = self.bot.last_post_time
                
            interval = (current_time - last_post).total_seconds()
            self.posting_intervals.append(interval)
            
            # Keep only last 50 intervals
            if len(self.posting_intervals) > 50:
                self.posting_intervals = self.posting_intervals[-50:]
                
            self.logger.info(f"📊 Post successful - Channel: {channel}, Interval: {interval/3600:.2f}h")
        
        # Reset consecutive failures
        self.consecutive_failures = 0

    def record_post_failure(self, channel: str, error: str):
        """Record a failed post attempt."""
        self.consecutive_failures += 1
        self.logger.warning(f"❌ Post failed - Channel: {channel}, Error: {error}")
        
        # Check for consecutive failure alert
        if self.consecutive_failures >= self.thresholds.max_consecutive_failures:
            self.send_alert(
                "consecutive_failures",
                f"🚨 {self.consecutive_failures} consecutive posting failures",
                {"channel": channel, "error": error}
            )

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        process = psutil.Process()
        
        return {
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent(),
            "uptime_hours": (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
        }

    def validate_posting_intervals(self) -> Dict[str, Any]:
        """Validate that posting intervals are within expected ranges."""
        if not self.posting_intervals:
            return {"status": "no_data", "message": "No posting intervals recorded yet"}
        
        recent_intervals = self.posting_intervals[-10:]  # Last 10 intervals
        avg_interval = sum(recent_intervals) / len(recent_intervals)
        
        validation = {
            "average_interval_hours": avg_interval / 3600,
            "expected_interval_hours": 3.0,
            "within_range": self.thresholds.min_posting_interval <= avg_interval <= self.thresholds.max_posting_interval,
            "recent_intervals": [i/3600 for i in recent_intervals[-5:]]  # Last 5 in hours
        }
        
        if not validation["within_range"]:
            self.send_alert(
                "posting_interval",
                f"⚠️ Posting interval out of range: {avg_interval/3600:.2f}h (expected: ~3h)",
                validation
            )
        
        return validation

    def create_metric_snapshot(self) -> MetricSnapshot:
        """Create a snapshot of current metrics."""
        system_metrics = self.get_system_metrics()
        
        # Calculate error rate
        total_attempts = len(self.posting_intervals) + self.consecutive_failures
        error_rate = self.consecutive_failures / max(total_attempts, 1)
        
        # Get next expected post time
        next_post = None
        if hasattr(self.bot, 'last_post_time') and hasattr(self.bot, 'auto_post_interval'):
            if self.bot.last_post_time and self.bot.auto_post_interval:
                last_post = self.bot.last_post_time
                if isinstance(last_post, str):
                    last_post = datetime.fromisoformat(last_post)
                    
                next_post = (last_post + timedelta(seconds=self.bot.auto_post_interval)).isoformat()
        
        return MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            posting_intervals=self.posting_intervals[-10:],  # Last 10
            memory_usage_mb=system_metrics["memory_mb"],
            cpu_percent=system_metrics["cpu_percent"],
            active_channels=getattr(self.bot, 'active_channel_count', 0),
            successful_posts=len(self.posting_intervals),
            failed_posts=self.consecutive_failures,
            error_rate=error_rate,
            uptime_hours=system_metrics["uptime_hours"],
            last_post_time=getattr(self.bot, 'last_post_time', None),
            next_expected_post=next_post
        )

    def check_system_health(self):
        """Check system health and send alerts if needed."""
        metrics = self.get_system_metrics()
        
        # Memory check
        if metrics["memory_mb"] > self.thresholds.max_memory_mb:
            self.send_alert(
                "high_memory",
                f"🔥 High memory usage: {metrics['memory_mb']:.1f}MB (limit: {self.thresholds.max_memory_mb}MB)",
                metrics
            )
        
        # CPU check
        if metrics["cpu_percent"] > self.thresholds.max_cpu_percent:
            self.send_alert(
                "high_cpu",
                f"⚡ High CPU usage: {metrics['cpu_percent']:.1f}% (limit: {self.thresholds.max_cpu_percent}%)",
                metrics
            )
        
        # Validate posting intervals
        self.validate_posting_intervals()

    def send_alert(self, alert_type: str, message: str, details: Dict = None):
        """Send an alert and log it."""
        current_time = datetime.now(timezone.utc)
        
        # Rate limiting: don't send same alert type more than once per hour
        if alert_type in self.last_alert_time:
            time_since_last = current_time - self.last_alert_time[alert_type]
            if time_since_last < timedelta(hours=1):
                return
        
        self.last_alert_time[alert_type] = current_time
        
        alert = {
            "timestamp": current_time.isoformat(),
            "type": alert_type,
            "message": message,
            "details": details or {}
        }
        
        # Log the alert
        self.logger.error(f"🚨 ALERT [{alert_type}]: {message}")
        
        # Save alert to file
        self.save_alert(alert)
        
        # TODO: Add Discord webhook or email notifications here
        # self.send_discord_notification(alert)

    def save_alert(self, alert: Dict):
        """Save alert to alerts file."""
        alerts = []
        
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r') as f:
                    alerts = json.load(f)
            except Exception:
                pass
        
        alerts.append(alert)
        
        # Keep only last 100 alerts
        alerts = alerts[-100:]
        
        self.alerts_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(self.alerts_file, 'w') as f:
                json.dump(alerts, f, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Failed to save alert: {e}")

    def save_metrics(self):
        """Save current metrics snapshot."""
        snapshot = self.create_metric_snapshot()
        
        # Load existing metrics
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    self.metrics_history = json.load(f)
            except Exception:
                self.metrics_history = []
        
        # Add new snapshot
        self.metrics_history.append(asdict(snapshot))
        
        # Keep only last 1000 snapshots (adjust as needed)
        self.metrics_history = self.metrics_history[-1000:]
        
        # Save to file
        self.metrics_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics_history, f, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Failed to save metrics: {e}")

    def get_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health report."""
        snapshot = self.create_metric_snapshot()
        interval_validation = self.validate_posting_intervals()
        
        # Calculate health score (0-100)
        health_score = 100
        
        # Deduct points for issues
        if snapshot.error_rate > 0:
            health_score -= min(snapshot.error_rate * 100, 30)
        
        if snapshot.memory_usage_mb > self.thresholds.max_memory_mb:
            health_score -= 20
            
        if snapshot.cpu_percent > self.thresholds.max_cpu_percent:
            health_score -= 15
            
        if not interval_validation.get("within_range", True):
            health_score -= 25
        
        health_score = max(0, health_score)
        
        return {
            "health_score": health_score,
            "status": "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical",
            "current_metrics": asdict(snapshot),
            "interval_validation": interval_validation,
            "alerts_last_24h": self.get_recent_alerts_count(),
            "uptime_hours": snapshot.uptime_hours,
            "last_check": datetime.now(timezone.utc).isoformat()
        }

    def get_recent_alerts_count(self) -> int:
        """Get count of alerts in the last 24 hours."""
        if not self.alerts_file.exists():
            return 0
            
        try:
            with open(self.alerts_file, 'r') as f:
                alerts = json.load(f)
                
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_alerts = [
                a for a in alerts 
                if datetime.fromisoformat(a["timestamp"]) > cutoff
            ]
            
            return len(recent_alerts)
        except Exception:
            return 0

    async def monitoring_loop(self):
        """Main monitoring loop - run this as a background task."""
        self.logger.info("🔍 Starting monitoring loop")
        
        while True:
            try:
                # Check system health
                self.check_system_health()
                
                # Save metrics snapshot every 15 minutes
                self.save_metrics()
                
                # Log health summary
                health_report = self.get_health_report()
                self.logger.info(
                    f"📊 Health: {health_report['health_score']}/100 "
                    f"({health_report['status']}) | "
                    f"Memory: {health_report['current_metrics']['memory_usage_mb']:.1f}MB | "
                    f"Uptime: {health_report['uptime_hours']:.1f}h"
                )
                
                # Wait 15 minutes
                await asyncio.sleep(15 * 60)
                
            except Exception as e:
                self.logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Monitoring utility functions
def create_monitoring_dashboard_data() -> Dict[str, Any]:
    """Create data for a monitoring dashboard."""
    metrics_file = Path("data/metrics_history.json")
    alerts_file = Path("data/alerts.json")
    
    dashboard_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "metrics": [],
        "alerts": []
    }
    
    # Load metrics
    if metrics_file.exists():
        try:
            with open(metrics_file, 'r') as f:
                dashboard_data["metrics"] = json.load(f)[-24:]  # Last 24 snapshots
        except Exception:
            pass
    
    # Load alerts
    if alerts_file.exists():
        try:
            with open(alerts_file, 'r') as f:
                all_alerts = json.load(f)
                # Get alerts from last 7 days
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                dashboard_data["alerts"] = [
                    a for a in all_alerts 
                    if datetime.fromisoformat(a["timestamp"]) > cutoff
                ]
        except Exception:
            pass
    
    return dashboard_data 