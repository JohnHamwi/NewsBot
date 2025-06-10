#!/usr/bin/env python
"""
Log Viewer Script

This script provides a command-line interface for viewing and analyzing structured logs
without needing to run the Discord bot.
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

# Set up colors for terminal output
COLORS = {
    "RESET": "\033[0m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
}

LEVEL_COLORS = {
    "DEBUG": COLORS["BLUE"],
    "INFO": COLORS["GREEN"],
    "WARNING": COLORS["YELLOW"],
    "ERROR": COLORS["RED"],
    "CRITICAL": COLORS["RED"] + COLORS["BOLD"],
}

def colorize(text: str, color: str) -> str:
    """Apply color to text."""
    return f"{color}{text}{COLORS['RESET']}"

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
                component: Optional[str] = None, user_id: Optional[str] = None,
                hours: Optional[int] = None) -> List[Dict[str, Any]]:
    """Filter logs based on criteria."""
    filtered = logs
    
    if level:
        filtered = [log for log in filtered if log.get('level') == level.upper()]
    
    if component:
        filtered = [log for log in filtered if log.get('component') == component]
    
    if user_id:
        filtered = [log for log in filtered if log.get('user_id') == user_id]
    
    if hours:
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()
        filtered = [log for log in filtered if log.get('timestamp', '') >= cutoff_str]
    
    return filtered

def print_log(log: Dict[str, Any], verbose: bool = False) -> None:
    """Print a log entry in a readable format."""
    timestamp = log.get('timestamp', '')
    if timestamp:
        try:
            dt = datetime.datetime.fromisoformat(timestamp)
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
    
    level = log.get('level', 'UNKNOWN')
    level_color = LEVEL_COLORS.get(level, COLORS['RESET'])
    message = log.get('message', '')
    component = log.get('component', '')
    
    # Format the basic log line
    log_line = f"{timestamp} {colorize(f'[{level}]', level_color)} "
    if component:
        log_line += f"{colorize(f'[{component}]', COLORS['CYAN'])} "
    log_line += message
    
    print(log_line)
    
    # Print additional details if verbose mode is enabled
    if verbose:
        for key, value in log.items():
            if key not in ['timestamp', 'level', 'message', 'component']:
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"  {key}: {value}")
        print()

def print_error_summary(logs: List[Dict[str, Any]]) -> None:
    """Print a summary of errors."""
    error_logs = [log for log in logs if log.get('level') in ['ERROR', 'CRITICAL']]
    
    if not error_logs:
        print(colorize("No errors found in logs.", COLORS['GREEN']))
        return
    
    print(colorize(f"\nError Summary ({len(error_logs)} errors):", COLORS['BOLD']))
    
    # Count errors by component
    components = {}
    for log in error_logs:
        component = log.get('component', 'unknown')
        components[component] = components.get(component, 0) + 1
    
    for component, count in sorted(components.items(), key=lambda x: x[1], reverse=True):
        print(f"  {colorize(component, COLORS['CYAN'])}: {count} errors")
    
    # Show recent errors
    print(colorize("\nRecent Errors:", COLORS['BOLD']))
    for log in error_logs[-5:]:
        timestamp = log.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                timestamp = dt.strftime('%H:%M:%S')
            except ValueError:
                pass
        message = log.get('message', '')
        component = log.get('component', 'unknown')
        print(f"  [{timestamp}] {colorize(component, COLORS['CYAN'])}: {message}")

def print_performance_metrics(logs: List[Dict[str, Any]]) -> None:
    """Print performance metrics from logs."""
    metrics = {}
    
    for log in logs:
        extras = log.get('extras', {})
        command_name = extras.get('command_name')
        duration = extras.get('duration')
        
        if command_name and duration is not None:
            if command_name not in metrics:
                metrics[command_name] = {
                    'count': 0,
                    'total_duration': 0,
                    'min_duration': float('inf'),
                    'max_duration': 0
                }
            
            metrics[command_name]['count'] += 1
            metrics[command_name]['total_duration'] += duration
            metrics[command_name]['min_duration'] = min(metrics[command_name]['min_duration'], duration)
            metrics[command_name]['max_duration'] = max(metrics[command_name]['max_duration'], duration)
    
    if not metrics:
        print(colorize("No performance metrics found in logs.", COLORS['YELLOW']))
        return
    
    print(colorize("\nPerformance Metrics:", COLORS['BOLD']))
    for command, data in sorted(metrics.items(), key=lambda x: x[1]['total_duration'], reverse=True):
        avg_duration = data['total_duration'] / data['count']
        print(f"  {colorize(command, COLORS['CYAN'])}:")
        print(f"    Count: {data['count']}")
        print(f"    Avg Duration: {avg_duration:.3f}s")
        print(f"    Min Duration: {data['min_duration']:.3f}s")
        print(f"    Max Duration: {data['max_duration']:.3f}s")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="View and analyze structured logs")
    parser.add_argument("--file", default="logs/newsbot_structured.json", help="Path to the log file")
    parser.add_argument("--level", choices=["debug", "info", "warning", "error", "critical"], help="Filter by log level")
    parser.add_argument("--component", help="Filter by component")
    parser.add_argument("--user", help="Filter by user ID")
    parser.add_argument("--hours", type=int, help="Only show logs from the last N hours")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of logs to display")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed log information")
    parser.add_argument("--errors", "-e", action="store_true", help="Show error summary")
    parser.add_argument("--performance", "-p", action="store_true", help="Show performance metrics")
    
    args = parser.parse_args()
    
    try:
        logs = load_logs(args.file)
        print(colorize(f"Loaded {len(logs)} log entries from {args.file}", COLORS['GREEN']))
        
        filtered_logs = filter_logs(
            logs, 
            level=args.level, 
            component=args.component, 
            user_id=args.user, 
            hours=args.hours
        )
        
        print(colorize(f"Filtered to {len(filtered_logs)} log entries", COLORS['GREEN']))
        
        if args.errors:
            print_error_summary(filtered_logs)
        
        if args.performance:
            print_performance_metrics(filtered_logs)
        
        # Display logs
        if len(filtered_logs) > 0:
            print(colorize("\nLog Entries:", COLORS['BOLD']))
            for log in filtered_logs[-args.limit:]:
                print_log(log, verbose=args.verbose)
            
            if len(filtered_logs) > args.limit:
                print(colorize(f"\nShowing {args.limit} of {len(filtered_logs)} logs. Use --limit to see more.", COLORS['YELLOW']))
    
    except Exception as e:
        print(colorize(f"Error: {str(e)}", COLORS['RED']))
        sys.exit(1)

if __name__ == "__main__":
    main() 