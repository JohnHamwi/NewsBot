# =============================================================================
# NewsBot Log Aggregator Module
# =============================================================================
# Log aggregation functionality for collecting, processing, and analyzing logs
# from the structured logging system with real-time processing and filtering
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# Log Entry Class
# =============================================================================
class LogEntry:
    """
    Represents a structured log entry with parsing and filtering capabilities.
    """

    def __init__(self, log_data: Dict[str, Any]):
        """
        Initialize a log entry from raw log data.

        Args:
            log_data: Raw log data from the structured logger
        """
        self.timestamp = datetime.fromisoformat(
            log_data.get("timestamp", datetime.utcnow().isoformat())
        )
        self.level = log_data.get("level", "UNKNOWN")
        self.message = log_data.get("message", "")
        self.logger = log_data.get("logger", "")
        self.request_id = log_data.get("request_id")
        self.user_id = log_data.get("user_id")
        self.command_name = log_data.get("command_name")
        self.component = log_data.get("component")
        self.extras = {
            k: v
            for k, v in log_data.items()
            if k
            not in [
                "timestamp",
                "level",
                "message",
                "logger",
                "request_id",
                "user_id",
                "command_name",
                "component",
            ]
        }

        # Extract exception info if available
        self.exception = log_data.get("exception")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the log entry to a dictionary.

        Returns:
            Dictionary representation of the log entry
        """
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "logger": self.logger,
        }

        if self.request_id:
            result["request_id"] = self.request_id
        if self.user_id:
            result["user_id"] = self.user_id
        if self.command_name:
            result["command_name"] = self.command_name
        if self.component:
            result["component"] = self.component
        if self.exception:
            result["exception"] = self.exception

        result.update(self.extras)
        return result

    def __str__(self) -> str:
        """
        Get a string representation of the log entry.

        Returns:
            String representation
        """
        return f"[{self.timestamp.isoformat()}] {self.level}: {self.message}"

# =============================================================================
# Log Aggregator Class
# =============================================================================
class LogAggregator:
    """
    Aggregates and analyzes logs from the structured logging system.

    Features:
    - Log collection from structured log files
    - Real-time log processing
    - Filter logs by various criteria
    - Error tracking and notification
    - Performance metric calculation
    - API for retrieving log data
    """

    def __init__(self, max_entries: int = 10000):
        """
        Initialize the log aggregator.

        Args:
            max_entries: Maximum number of log entries to keep in memory
        """
        self.max_entries = max_entries
        self.entries: deque = deque(maxlen=max_entries)
        self.request_index: Dict[str, List[LogEntry]] = defaultdict(list)
        self.user_index: Dict[str, List[LogEntry]] = defaultdict(list)
        self.command_index: Dict[str, List[LogEntry]] = defaultdict(list)
        self.component_index: Dict[str, List[LogEntry]] = defaultdict(list)
        self.level_index: Dict[str, List[LogEntry]] = defaultdict(list)

        # Performance metrics
        self.command_durations: Dict[str, List[float]] = defaultdict(list)

        # Error tracking
        self.errors: List[LogEntry] = []
        self.error_count_by_component: Dict[str, int] = defaultdict(int)

        # Processing state
        self.last_processed_time = datetime.min
        self._running = False
        self._lock = threading.RLock()

    # =========================================================================
    # Core Processing Methods
    # =========================================================================
    async def start(self):
        """
        Start the log aggregator.
        """
        if self._running:
            return

        self._running = True
        asyncio.create_task(self._process_logs_task())

    async def stop(self):
        """
        Stop the log aggregator.
        """
        self._running = False

    async def _process_logs_task(self):
        """
        Background task to process logs.
        """
        while self._running:
            try:
                await self._process_logs()
                await asyncio.sleep(5)  # Process every 5 seconds
            except Exception as e:
                print(f"Error processing logs: {e}")
                await asyncio.sleep(30)  # Longer sleep on error

    async def _process_logs(self):
        """
        Process new log entries from the structured log file.
        """
        log_file = "logs/newsbot_structured.json"
        if not os.path.exists(log_file):
            return

        # Get file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(log_file))
        if mod_time <= self.last_processed_time:
            return  # No changes since last processing

        self.last_processed_time = mod_time

        # Read and process the log file
        try:
            with open(log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        log_data = json.loads(line)
                        await self.process_log_entry(log_data)
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
        except Exception as e:
            print(f"Error reading log file: {e}")

    async def process_log_entry(self, log_data: Dict[str, Any]):
        """
        Process a single log entry.

        Args:
            log_data: Raw log data dictionary
        """
        try:
            entry = LogEntry(log_data)

            with self._lock:
                # Add to main entries
                self.entries.append(entry)

                # Update indexes
                if entry.request_id:
                    self.request_index[entry.request_id].append(entry)
                if entry.user_id:
                    self.user_index[entry.user_id].append(entry)
                if entry.command_name:
                    self.command_index[entry.command_name].append(entry)
                if entry.component:
                    self.component_index[entry.component].append(entry)
                self.level_index[entry.level].append(entry)

                # Track errors
                if entry.level in ["ERROR", "CRITICAL"]:
                    self.errors.append(entry)
                    if entry.component:
                        self.error_count_by_component[entry.component] += 1

                # Track command durations if available
                if entry.command_name and "duration" in entry.extras:
                    try:
                        duration = float(entry.extras["duration"])
                        self.command_durations[entry.command_name].append(duration)
                    except (ValueError, TypeError):
                        pass

        except Exception as e:
            print(f"Error processing log entry: {e}")

    # =========================================================================
    # Query and Retrieval Methods
    # =========================================================================
    def get_logs(
        self,
        level: Optional[str] = None,
        component: Optional[str] = None,
        command: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get filtered log entries.

        Args:
            level: Filter by log level
            component: Filter by component
            command: Filter by command name
            user_id: Filter by user ID
            request_id: Filter by request ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of entries to return

        Returns:
            List of log entries as dictionaries
        """
        with self._lock:
            # Start with candidates based on the most specific filter
            candidates = []

            if request_id and request_id in self.request_index:
                candidates = self.request_index[request_id]
            elif user_id and user_id in self.user_index:
                candidates = self.user_index[user_id]
            elif command and command in self.command_index:
                candidates = self.command_index[command]
            elif component and component in self.component_index:
                candidates = self.component_index[component]
            elif level and level in self.level_index:
                candidates = self.level_index[level]
            else:
                candidates = list(self.entries)

            # Apply remaining filters
            result = []
            for entry in candidates:
                if level and entry.level != level:
                    continue
                if component and entry.component != component:
                    continue
                if command and entry.command_name != command:
                    continue
                if user_id and entry.user_id != user_id:
                    continue
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue

                result.append(entry.to_dict())

                if len(result) >= limit:
                    break

            return result

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get a summary of errors in the specified time window.

        Args:
            hours: Number of hours to look back

        Returns:
            Error summary
        """
        with self._lock:
            start_time = datetime.utcnow() - timedelta(hours=hours)

            # Filter errors by time
            recent_errors = [e for e in self.errors if e.timestamp >= start_time]

            # Group by component
            errors_by_component = defaultdict(list)
            for error in recent_errors:
                component = error.component or "unknown"
                errors_by_component[component].append(error)

            # Calculate statistics
            result = {
                "total_count": len(recent_errors),
                "by_component": {
                    component: len(errors)
                    for component, errors in errors_by_component.items()
                },
                "recent": [e.to_dict() for e in recent_errors[-10:]],  # Last 10 errors
            }

            return result

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for commands.

        Returns:
            Performance metrics
        """
        with self._lock:
            metrics = {}

            for command, durations in self.command_durations.items():
                if not durations:
                    continue

                metrics[command] = {
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                }

            return metrics

    def get_request_trace(self, request_id: str) -> List[Dict[str, Any]]:
        """
        Get all log entries for a specific request, sorted by timestamp.

        Args:
            request_id: Request ID to trace

        Returns:
            List of log entries for the request
        """
        with self._lock:
            if request_id not in self.request_index:
                return []

            entries = self.request_index[request_id]
            sorted_entries = sorted(entries, key=lambda e: e.timestamp)

            return [e.to_dict() for e in sorted_entries]

    def get_user_activity(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get activity for a specific user in the specified time window.

        Args:
            user_id: User ID
            hours: Number of hours to look back

        Returns:
            List of log entries for the user
        """
        with self._lock:
            if user_id not in self.user_index:
                return []

            start_time = datetime.utcnow() - timedelta(hours=hours)

            entries = [e for e in self.user_index[user_id] if e.timestamp >= start_time]
            sorted_entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)

            return [e.to_dict() for e in sorted_entries]


# Global instance
log_aggregator = LogAggregator()


async def initialize_log_aggregator():
    """
    Initialize and start the log aggregator.
    """
    await log_aggregator.start()
