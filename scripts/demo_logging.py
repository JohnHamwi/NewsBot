#!/usr/bin/env python
"""
Structured Logging Demo Script

This script demonstrates all the features of the structured logging system
without requiring a running bot or manual command execution.
"""

import os
import sys
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.structured_logger import structured_logger, LogContext
from src.utils.logging_decorators import log_function, log_method, log_task
from src.monitoring.log_aggregator import initialize_log_aggregator, log_aggregator

class LoggingDemo:
    """Class to demonstrate structured logging features."""
    
    def __init__(self):
        """Initialize the demo."""
        self.component = "LoggingDemo"
        self.log_file = "logs/newsbot_structured.json"
    
    @log_method(component="Demo")
    def basic_logging(self):
        """Demonstrate basic logging capabilities."""
        print("\n[1] Basic Logging Capabilities")
        print("-" * 50)
        
        # Basic logging with different levels
        structured_logger.debug("This is a debug message")
        structured_logger.info("This is an info message")
        structured_logger.warning("This is a warning message")
        structured_logger.error("This is an error message", exc_info=False)
        
        # Logging with extra fields
        structured_logger.info("Message with extra fields", extras={
            "user_id": "12345",
            "command": "test_command",
            "custom_field": "custom_value"
        })
        
        # Logging with context
        with LogContext(user_id="67890", component="ContextDemo"):
            structured_logger.info("Message with context")
            
            # Nested context
            with LogContext(request_id="req-123"):
                structured_logger.info("Message with nested context")
        
        print("✅ Basic logging demonstrated. Check logs/newsbot_structured.json for output.")
    
    @log_method(component="Demo")
    def performance_tracking(self):
        """Demonstrate performance tracking capabilities."""
        print("\n[2] Performance Tracking")
        print("-" * 50)
        
        # Start a timer
        timer_id = structured_logger.start_timer("demo_operation")
        
        # Simulate some work
        time.sleep(0.5)
        
        # Stop the timer
        duration = structured_logger.stop_timer(timer_id)
        print(f"✅ Operation took {duration:.3f} seconds")
        
        # Command tracking
        structured_logger.command("test_command", 0.75, extras={
            "user_id": "12345",
            "guild_id": "67890"
        })
        
        # Get metrics
        metrics = structured_logger.get_metrics()
        print("✅ Performance metrics:", json.dumps(metrics, indent=2))
    
    @log_function(component="Demo")
    def error_handling(self):
        """Demonstrate error handling and tracking."""
        print("\n[3] Error Handling")
        print("-" * 50)
        
        try:
            # Intentionally raise an exception
            raise ValueError("This is a test exception")
        except Exception as e:
            structured_logger.error(
                "An error occurred during the demo",
                extras={"operation": "error_demo"},
                exc_info=True
            )
            print("✅ Error logged with full traceback")
    
    @log_task(component="Demo")
    async def async_task_demo(self):
        """Demonstrate async task logging."""
        print("\n[4] Async Task Logging")
        print("-" * 50)
        
        print("Starting async task...")
        await asyncio.sleep(0.5)
        print("✅ Async task completed and logged")
        
        return "Task completed"
    
    async def aggregator_demo(self):
        """Demonstrate log aggregator capabilities."""
        print("\n[5] Log Aggregator Features")
        print("-" * 50)
        
        # Initialize the log aggregator
        print("Initializing log aggregator...")
        await initialize_log_aggregator()
        print("✅ Log aggregator initialized")
        
        # Get recent logs
        print("\nRetrieving recent logs:")
        logs = log_aggregator.get_logs(limit=5)
        for log in logs:
            timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%H:%M:%S")
            print(f"  [{timestamp}] [{log['level']}] {log['message']}")
        
        # Get error summary
        print("\nError summary:")
        error_summary = log_aggregator.get_error_summary(hours=24)
        print(f"  Total errors: {error_summary['total_count']}")
        for component, count in error_summary.get('by_component', {}).items():
            if count > 0:
                print(f"  - {component}: {count}")
        
        # Get performance metrics
        print("\nPerformance metrics:")
        perf_metrics = log_aggregator.get_performance_metrics()
        for command, metrics in perf_metrics.items():
            print(f"  - {command}: {metrics['avg_duration']:.3f}s avg ({metrics['count']} calls)")
        
        # Check user activity
        print("\nUser activity:")
        user_activity = log_aggregator.get_user_activity("12345", hours=24)
        for activity in user_activity:
            timestamp = datetime.fromisoformat(activity["timestamp"]).strftime("%H:%M:%S")
            print(f"  [{timestamp}] {activity['message']}")
            
        print("\n✅ Log aggregator features demonstrated")
    
    async def run_demo(self):
        """Run the full demo."""
        print("\n=== STRUCTURED LOGGING DEMO ===\n")
        
        # Ensure the logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Run demos
        self.basic_logging()
        self.performance_tracking()
        self.error_handling()
        await self.async_task_demo()
        await self.aggregator_demo()
        
        print("\n=== DEMO COMPLETED ===")
        print(f"All logs have been written to {self.log_file}")
        print("You can inspect this file to see the structured JSON logs.")

async def main():
    """Main entry point."""
    demo = LoggingDemo()
    await demo.run_demo()

if __name__ == "__main__":
    asyncio.run(main()) 