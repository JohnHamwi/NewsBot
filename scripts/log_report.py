#!/usr/bin/env python
"""
Log Report Generator

This script generates PDF reports from structured logs, allowing for easy
visualization and sharing of log data.
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from fpdf import FPDF
import numpy as np

# Add the project root to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

class LogReport:
    """Generate reports from structured logs."""
    
    def __init__(self, logs: List[Dict[str, Any]], title: str = "NewsBot Log Report"):
        """Initialize with logs data."""
        self.logs = logs
        self.title = title
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.setup_pdf()
    
    def setup_pdf(self):
        """Set up the PDF with title and header."""
        self.pdf.set_font("Arial", "B", 16)
        self.pdf.cell(0, 10, self.title, 0, 1, "C")
        self.pdf.set_font("Arial", "I", 10)
        self.pdf.cell(0, 5, f"Generated on {self.timestamp}", 0, 1, "C")
        self.pdf.ln(5)
    
    def add_summary(self):
        """Add a summary section to the report."""
        total_logs = len(self.logs)
        levels = {}
        components = {}
        errors = []
        
        # Extract timestamps for time range
        timestamps = []
        for log in self.logs:
            if "timestamp" in log:
                try:
                    timestamp = datetime.datetime.fromisoformat(log["timestamp"])
                    timestamps.append(timestamp)
                except (ValueError, TypeError):
                    pass
            
            level = log.get("level", "UNKNOWN")
            levels[level] = levels.get(level, 0) + 1
            
            component = log.get("component", "unknown")
            components[component] = components.get(component, 0) + 1
            
            if level in ["ERROR", "CRITICAL"]:
                errors.append(log)
        
        # Time range
        time_range = "N/A"
        if timestamps:
            min_time = min(timestamps)
            max_time = max(timestamps)
            time_range = f"{min_time.strftime('%Y-%m-%d %H:%M')} to {max_time.strftime('%Y-%m-%d %H:%M')}"
        
        # Add summary to PDF
        self.pdf.set_font("Arial", "B", 14)
        self.pdf.cell(0, 10, "Summary", 0, 1, "L")
        
        self.pdf.set_font("Arial", "", 11)
        self.pdf.cell(0, 6, f"Total Logs: {total_logs}", 0, 1, "L")
        self.pdf.cell(0, 6, f"Time Range: {time_range}", 0, 1, "L")
        self.pdf.cell(0, 6, f"Error Count: {len(errors)}", 0, 1, "L")
        
        # Add log level breakdown
        self.pdf.ln(5)
        self.pdf.set_font("Arial", "B", 12)
        self.pdf.cell(0, 8, "Log Level Distribution", 0, 1, "L")
        
        self.pdf.set_font("Arial", "", 11)
        for level, count in sorted(levels.items()):
            percentage = (count / total_logs) * 100
            self.pdf.cell(0, 6, f"{level}: {count} ({percentage:.1f}%)", 0, 1, "L")
        
        # Add component breakdown
        self.pdf.ln(5)
        self.pdf.set_font("Arial", "B", 12)
        self.pdf.cell(0, 8, "Component Distribution", 0, 1, "L")
        
        self.pdf.set_font("Arial", "", 11)
        for component, count in sorted(components.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / total_logs) * 100
            self.pdf.cell(0, 6, f"{component}: {count} ({percentage:.1f}%)", 0, 1, "L")
        
        # Add a page break
        self.pdf.add_page()
        
        # Generate level distribution chart
        self.generate_level_chart(levels)
        
        # Add the chart to the PDF
        self.pdf.image("temp_level_chart.png", x=10, y=None, w=180)
        plt.close()
        os.remove("temp_level_chart.png")
        
        # Generate component distribution chart
        self.generate_component_chart(components)
        
        # Add the chart to the PDF
        self.pdf.image("temp_component_chart.png", x=10, y=None, w=180)
        plt.close()
        os.remove("temp_component_chart.png")
    
    def generate_level_chart(self, levels: Dict[str, int]):
        """Generate a chart for log level distribution."""
        plt.figure(figsize=(10, 6))
        colors = {
            "DEBUG": "blue",
            "INFO": "green",
            "WARNING": "orange",
            "ERROR": "red",
            "CRITICAL": "darkred",
            "UNKNOWN": "gray"
        }
        
        labels = list(levels.keys())
        values = list(levels.values())
        chart_colors = [colors.get(level, "gray") for level in labels]
        
        plt.bar(labels, values, color=chart_colors)
        plt.title("Log Level Distribution")
        plt.xlabel("Log Level")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig("temp_level_chart.png")
    
    def generate_component_chart(self, components: Dict[str, int]):
        """Generate a chart for component distribution."""
        # Take top 10 components by count
        top_components = sorted(components.items(), key=lambda x: x[1], reverse=True)[:10]
        labels = [item[0] for item in top_components]
        values = [item[1] for item in top_components]
        
        plt.figure(figsize=(10, 6))
        plt.bar(labels, values, color="skyblue")
        plt.title("Top 10 Components by Log Count")
        plt.xlabel("Component")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig("temp_component_chart.png")
    
    def add_error_section(self):
        """Add a section for errors to the report."""
        # Filter error logs
        error_logs = [log for log in self.logs if log.get("level") in ["ERROR", "CRITICAL"]]
        
        if not error_logs:
            return
        
        self.pdf.add_page()
        self.pdf.set_font("Arial", "B", 14)
        self.pdf.cell(0, 10, "Error Summary", 0, 1, "L")
        
        # Group errors by component
        errors_by_component = {}
        for log in error_logs:
            component = log.get("component", "unknown")
            if component not in errors_by_component:
                errors_by_component[component] = []
            errors_by_component[component].append(log)
        
        # Add error breakdown
        self.pdf.set_font("Arial", "B", 12)
        self.pdf.cell(0, 8, "Errors by Component", 0, 1, "L")
        
        self.pdf.set_font("Arial", "", 11)
        for component, logs in sorted(errors_by_component.items()):
            self.pdf.cell(0, 6, f"{component}: {len(logs)} errors", 0, 1, "L")
        
        # Add recent errors
        self.pdf.ln(5)
        self.pdf.set_font("Arial", "B", 12)
        self.pdf.cell(0, 8, "Recent Errors", 0, 1, "L")
        
        # Sort by timestamp
        try:
            recent_errors = sorted(
                error_logs, 
                key=lambda x: datetime.datetime.fromisoformat(x.get("timestamp", "1970-01-01T00:00:00")),
                reverse=True
            )[:10]
        except:
            recent_errors = error_logs[-10:]
        
        for log in recent_errors:
            timestamp = log.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            
            message = log.get("message", "")
            component = log.get("component", "unknown")
            
            self.pdf.set_font("Arial", "B", 10)
            self.pdf.cell(0, 6, f"{timestamp} - {component}", 0, 1, "L")
            
            self.pdf.set_font("Arial", "", 10)
            # Handle multiline messages
            message_lines = message.split("\n")
            for line in message_lines[:3]:  # Only show first 3 lines
                self.pdf.cell(0, 5, line[:100], 0, 1, "L")
            
            # Add a small gap between errors
            self.pdf.ln(2)
    
    def add_performance_section(self):
        """Add a section for performance metrics to the report."""
        # Extract performance data
        performance_data = {}
        timestamps = []
        
        for log in self.logs:
            extras = log.get("extras", {})
            metric_name = extras.get("metric_name")
            duration = extras.get("duration")
            timestamp = log.get("timestamp")
            
            if metric_name and duration is not None and timestamp:
                try:
                    dt = datetime.datetime.fromisoformat(timestamp)
                    if metric_name not in performance_data:
                        performance_data[metric_name] = {"timestamps": [], "durations": []}
                    
                    performance_data[metric_name]["timestamps"].append(dt)
                    performance_data[metric_name]["durations"].append(duration)
                    timestamps.append(dt)
                except (ValueError, TypeError):
                    pass
        
        if not performance_data:
            return
        
        self.pdf.add_page()
        self.pdf.set_font("Arial", "B", 14)
        self.pdf.cell(0, 10, "Performance Metrics", 0, 1, "L")
        
        # Add performance metrics table
        self.pdf.set_font("Arial", "B", 11)
        self.pdf.cell(60, 10, "Metric", 1, 0, "L")
        self.pdf.cell(30, 10, "Count", 1, 0, "C")
        self.pdf.cell(30, 10, "Avg (s)", 1, 0, "C")
        self.pdf.cell(30, 10, "Min (s)", 1, 0, "C")
        self.pdf.cell(30, 10, "Max (s)", 1, 1, "C")
        
        self.pdf.set_font("Arial", "", 11)
        for metric, data in sorted(performance_data.items()):
            durations = data["durations"]
            count = len(durations)
            avg_duration = sum(durations) / count if count > 0 else 0
            min_duration = min(durations) if durations else 0
            max_duration = max(durations) if durations else 0
            
            # Truncate metric name if too long
            metric_display = metric[:55] + "..." if len(metric) > 55 else metric
            
            self.pdf.cell(60, 8, metric_display, 1, 0, "L")
            self.pdf.cell(30, 8, str(count), 1, 0, "C")
            self.pdf.cell(30, 8, f"{avg_duration:.3f}", 1, 0, "C")
            self.pdf.cell(30, 8, f"{min_duration:.3f}", 1, 0, "C")
            self.pdf.cell(30, 8, f"{max_duration:.3f}", 1, 1, "C")
        
        # Generate performance trend chart for top metrics
        if timestamps:
            top_metrics = sorted(
                performance_data.items(),
                key=lambda x: sum(x[1]["durations"]),
                reverse=True
            )[:5]
            
            if top_metrics:
                self.generate_performance_chart(top_metrics)
                self.pdf.ln(5)
                self.pdf.image("temp_performance_chart.png", x=10, y=None, w=180)
                plt.close()
                os.remove("temp_performance_chart.png")
    
    def generate_performance_chart(self, metrics):
        """Generate a line chart for performance metrics over time."""
        plt.figure(figsize=(10, 6))
        
        for metric_name, data in metrics:
            timestamps = data["timestamps"]
            durations = data["durations"]
            
            # Create a shorter display name for the legend
            display_name = metric_name
            if len(display_name) > 25:
                parts = display_name.split('.')
                if len(parts) > 1:
                    display_name = parts[-1]
                else:
                    display_name = display_name[:22] + "..."
            
            plt.plot(timestamps, durations, marker='o', linestyle='-', label=display_name)
        
        plt.title("Performance Metrics Over Time")
        plt.xlabel("Time")
        plt.ylabel("Duration (seconds)")
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        plt.savefig("temp_performance_chart.png")
    
    def generate_report(self, output_file: str):
        """Generate the complete PDF report."""
        self.add_summary()
        self.add_error_section()
        self.add_performance_section()
        self.pdf.output(output_file)
        print(f"Report generated: {output_file}")

def load_logs(file_path: str) -> List[Dict[str, Any]]:
    """Load logs from a file."""
    if not os.path.exists(file_path):
        print(f"Error: Log file {file_path} not found.")
        sys.exit(1)
        
    logs = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                log = json.loads(line.strip())
                logs.append(log)
            except json.JSONDecodeError:
                continue
    
    return logs

def filter_logs(logs: List[Dict[str, Any]], level: Optional[str] = None, 
               component: Optional[str] = None, hours: Optional[int] = None) -> List[Dict[str, Any]]:
    """Filter logs based on criteria."""
    filtered = logs
    
    if level:
        filtered = [log for log in filtered if log.get('level') == level.upper()]
    
    if component:
        filtered = [log for log in filtered if log.get('component') == component]
    
    if hours:
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()
        filtered = [log for log in filtered if log.get('timestamp', '') >= cutoff_str]
    
    return filtered

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate PDF reports from structured logs")
    parser.add_argument("--file", default="logs/newsbot_structured.json", help="Path to the log file")
    parser.add_argument("--output", default="log_report.pdf", help="Output PDF file name")
    parser.add_argument("--title", default="NewsBot Log Report", help="Report title")
    parser.add_argument("--level", choices=["debug", "info", "warning", "error", "critical"], help="Filter by log level")
    parser.add_argument("--component", help="Filter by component")
    parser.add_argument("--hours", type=int, help="Only include logs from the last N hours")
    
    args = parser.parse_args()
    
    try:
        # Ensure matplotlib is available
        try:
            import matplotlib
        except ImportError:
            print("Error: matplotlib is required for this script.")
            print("Install it with: pip install matplotlib")
            sys.exit(1)
        
        # Ensure FPDF is available
        try:
            from fpdf import FPDF
        except ImportError:
            print("Error: fpdf is required for this script.")
            print("Install it with: pip install fpdf")
            sys.exit(1)
        
        logs = load_logs(args.file)
        print(f"Loaded {len(logs)} log entries from {args.file}")
        
        filtered_logs = filter_logs(
            logs, 
            level=args.level, 
            component=args.component, 
            hours=args.hours
        )
        
        print(f"Filtered to {len(filtered_logs)} log entries")
        
        if not filtered_logs:
            print("No logs match the specified criteria.")
            sys.exit(1)
        
        report = LogReport(filtered_logs, title=args.title)
        report.generate_report(args.output)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 