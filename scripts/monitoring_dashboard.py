#!/usr/bin/env python3
"""
NewsBot Monitoring Dashboard

A simple terminal-based dashboard to view bot health and metrics.
Run this script to see current bot status, performance metrics, and recent alerts.
"""

import json
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

try:
    from src.monitoring.production_monitor import create_monitoring_dashboard_data
except ImportError:
    try:
        from monitoring.production_monitor import create_monitoring_dashboard_data
    except ImportError:
        print("❌ Could not import monitoring module. Make sure you're running from the project root.")
        sys.exit(1)

def print_colored(text, color_code):
    """Print colored text."""
    print(f"\033[{color_code}m{text}\033[0m")

def print_header(title):
    """Print a section header."""
    print("\n" + "="*60)
    print_colored(f"  {title}", "1;36")  # Bold cyan
    print("="*60)

def print_metric(label, value, good_threshold=None, warning_threshold=None, color_override=None):
    """Print a metric with color coding based on thresholds."""
    if color_override:
        color = color_override
    elif good_threshold and warning_threshold:
        if value <= good_threshold:
            color = "32"  # Green
        elif value <= warning_threshold:
            color = "33"  # Yellow
        else:
            color = "31"  # Red
    else:
        color = "37"  # White
    
    print(f"  {label:<30} \033[{color}m{value}\033[0m")

def format_time_ago(timestamp_str):
    """Format a timestamp as 'X hours ago'."""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - timestamp
        
        if delta.days > 0:
            return f"{delta.days} days ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hours ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    except:
        return "Unknown"

def display_health_summary(data):
    """Display overall health summary."""
    print_header("🏥 SYSTEM HEALTH")
    
    if not data["metrics"]:
        print_colored("  ❌ No metrics data available", "31")
        return
    
    latest = data["metrics"][-1]
    
    # Calculate health score
    health_score = 100
    status_color = "32"  # Green
    status_text = "HEALTHY"
    
    # Check various health indicators
    if latest["error_rate"] > 0.1:
        health_score -= 30
        status_color = "31"
        status_text = "CRITICAL"
    elif latest["error_rate"] > 0.05:
        health_score -= 15
        status_color = "33"
        status_text = "WARNING"
    
    if latest["memory_usage_mb"] > 500:
        health_score -= 20
        if status_text == "HEALTHY":
            status_color = "33"
            status_text = "WARNING"
    
    health_score = max(0, health_score)
    
    print_colored(f"  Overall Status: {status_text} ({health_score}/100)", status_color)
    print_metric("Uptime", f"{latest['uptime_hours']:.1f} hours")
    print_metric("Memory Usage", f"{latest['memory_usage_mb']:.1f} MB", 200, 400)
    print_metric("CPU Usage", f"{latest['cpu_percent']:.1f}%", 30, 60)
    print_metric("Error Rate", f"{latest['error_rate']:.1%}", 0.02, 0.05)
    print_metric("Successful Posts", str(latest['successful_posts']))
    print_metric("Failed Posts", str(latest['failed_posts']))

def display_posting_metrics(data):
    """Display posting interval metrics."""
    print_header("📊 POSTING METRICS")
    
    if not data["metrics"]:
        print_colored("  ❌ No metrics data available", "31")
        return
    
    latest = data["metrics"][-1]
    
    if latest["last_post_time"]:
        last_post_ago = format_time_ago(latest["last_post_time"])
        print_metric("Last Post", last_post_ago)
    else:
        print_metric("Last Post", "Never")
    
    if latest["next_expected_post"]:
        next_post_ago = format_time_ago(latest["next_expected_post"])
        print_metric("Next Expected Post", next_post_ago)
    
    # Show recent posting intervals
    if latest["posting_intervals"]:
        intervals_hours = [i/3600 for i in latest["posting_intervals"]]
        avg_interval = sum(intervals_hours) / len(intervals_hours)
        print_metric("Average Interval", f"{avg_interval:.1f} hours", 2.8, 3.2)
        
        print("\n  Recent Intervals:")
        for i, interval in enumerate(intervals_hours[-5:], 1):
            color = "32" if 2.5 <= interval <= 3.5 else "33" if 2.0 <= interval <= 4.0 else "31"
            print(f"    {i}. \033[{color}m{interval:.1f}h\033[0m")

def display_recent_alerts(data):
    """Display recent alerts."""
    print_header("🚨 RECENT ALERTS")
    
    if not data["alerts"]:
        print_colored("  ✅ No alerts in the last 7 days", "32")
        return
    
    # Group alerts by type
    alert_counts = {}
    recent_alerts = []
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    
    for alert in data["alerts"]:
        alert_time = datetime.fromisoformat(alert["timestamp"])
        alert_type = alert["type"]
        
        if alert_type not in alert_counts:
            alert_counts[alert_type] = 0
        alert_counts[alert_type] += 1
        
        if alert_time > cutoff:
            recent_alerts.append(alert)
    
    # Show alert counts by type
    print("  Alert Counts (Last 7 days):")
    for alert_type, count in alert_counts.items():
        color = "31" if count > 5 else "33" if count > 2 else "37"
        print(f"    {alert_type:<20} \033[{color}m{count}\033[0m")
    
    # Show recent alerts (last 24h)
    if recent_alerts:
        print(f"\n  Last 24 Hours ({len(recent_alerts)} alerts):")
        for alert in recent_alerts[-5:]:  # Show last 5
            time_ago = format_time_ago(alert["timestamp"])
            print(f"    \033[31m[{alert['type']}]\033[0m {alert['message']} ({time_ago})")

def display_performance_trend(data):
    """Display performance trend."""
    print_header("📈 PERFORMANCE TREND")
    
    if len(data["metrics"]) < 2:
        print_colored("  ❌ Not enough data for trend analysis", "31")
        return
    
    # Compare last 6 hours vs previous 6 hours
    recent_metrics = data["metrics"][-6:]
    older_metrics = data["metrics"][-12:-6] if len(data["metrics"]) >= 12 else data["metrics"][:-6]
    
    if not older_metrics:
        print_colored("  ❌ Not enough historical data", "31")
        return
    
    # Calculate averages
    def avg_metric(metrics, key):
        values = [m[key] for m in metrics if m[key] is not None]
        return sum(values) / len(values) if values else 0
    
    recent_memory = avg_metric(recent_metrics, "memory_usage_mb")
    older_memory = avg_metric(older_metrics, "memory_usage_mb")
    memory_change = recent_memory - older_memory
    
    recent_cpu = avg_metric(recent_metrics, "cpu_percent")
    older_cpu = avg_metric(older_metrics, "cpu_percent")
    cpu_change = recent_cpu - older_cpu
    
    # Display trends
    def trend_arrow(change):
        if abs(change) < 0.1:
            return "→", "37"  # Stable
        elif change > 0:
            return "↗", "31"  # Increasing (bad)
        else:
            return "↘", "32"  # Decreasing (good)
    
    memory_arrow, memory_color = trend_arrow(memory_change)
    cpu_arrow, cpu_color = trend_arrow(cpu_change)
    
    print(f"  Memory Usage:     \033[{memory_color}m{memory_arrow} {memory_change:+.1f} MB\033[0m")
    print(f"  CPU Usage:        \033[{cpu_color}m{cpu_arrow} {cpu_change:+.1f}%\033[0m")

def display_backup_status():
    """Display backup system status."""
    print_header("🗄️ BACKUP STATUS")
    
    try:
        from src.monitoring.backup_scheduler import BackupScheduler
        scheduler = BackupScheduler()
        status = scheduler.get_backup_status()
        
        if "error" in status:
            print_colored(f"  ❌ Backup system error: {status['error']}", "31")
            return
        
        # Basic backup info
        enabled_color = "32" if status["enabled"] else "31"
        enabled_text = "Enabled" if status["enabled"] else "Disabled"
        print_metric("Backup System", enabled_text, color_override=enabled_color)
        print_metric("Total Backups", str(status["total_backups"]))
        
        if status["total_size_mb"] > 0:
            size_mb = status["total_size_mb"]
            size_color = "32" if size_mb < 100 else "33" if size_mb < 500 else "31"
            print_metric("Total Size", f"{size_mb:.1f} MB", color_override=size_color)
        
        if status["last_backup"]:
            last_backup_ago = format_time_ago(status["last_backup"])
            print_metric("Last Backup", last_backup_ago)
        else:
            print_metric("Last Backup", "Never", color_override="31")
        
        # Recent backups
        if status["recent_backups"]:
            print("\n  Recent Backups:")
            for backup in status["recent_backups"][:3]:
                backup_time = format_time_ago(backup["timestamp"])
                size_mb = backup["size_mb"]
                print(f"    • {backup['type']} - {backup_time} ({size_mb:.1f}MB)")
        
    except ImportError:
        print_colored("  ⚠️ Backup system not available (missing dependencies)", "33")
    except Exception as e:
        print_colored(f"  ❌ Error getting backup status: {e}", "31")

def main():
    """Main dashboard function."""
    print_colored("🤖 NewsBot Monitoring Dashboard", "1;35")
    print_colored(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "37")
    
    try:
        dashboard_data = create_monitoring_dashboard_data()
    except Exception as e:
        print_colored(f"❌ Error loading monitoring data: {e}", "31")
        return
    
    # Display all sections
    display_health_summary(dashboard_data)
    display_posting_metrics(dashboard_data)
    display_recent_alerts(dashboard_data)
    display_performance_trend(dashboard_data)
    display_backup_status()
    
    print_header("📝 QUICK COMMANDS")
    print("  View logs:        tail -f logs/newsbot.log")
    print("  View monitoring:  tail -f logs/monitoring.log")
    print("  Run tests:        ./scripts/run_tests.sh critical")
    print("  Create backup:    python scripts/backup_manager.py create")
    print("  Backup status:    python scripts/backup_manager.py status")
    print("  Health check:     python scripts/monitoring_dashboard.py")
    print()

if __name__ == "__main__":
    main() 