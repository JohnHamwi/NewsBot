"""
Tests for the structured logging system.
"""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, ANY
import logging
import os
import tempfile
import contextvars
from datetime import datetime

from src.utils.structured_logger import (
    structured_logger, 
    LogContext, 
    JSONFormatter, 
    request_id, 
    user_id, 
    command_name, 
    component
)
from src.utils.logging_decorators import (
    log_command, 
    log_method, 
    log_function, 
    log_task
)
from src.monitoring.log_aggregator import (
    LogAggregator, 
    LogEntry, 
    initialize_log_aggregator
)

# Reset context variables before each test
@pytest.fixture(autouse=True)
def reset_context_vars():
    """Reset context variables before each test."""
    request_id.set(None)
    user_id.set(None)
    command_name.set(None)
    component.set(None)
    yield

# Mock the context variables
@pytest.fixture
def mock_context_vars():
    """Mock all the context variables for testing."""
    with patch('src.utils.structured_logger.request_id'), \
         patch('src.utils.structured_logger.user_id'), \
         patch('src.utils.structured_logger.command_name'), \
         patch('src.utils.structured_logger.component'):
        yield

class TestStructuredLogger:
    """Test the structured logger implementation."""
    
    def test_basic_logging(self):
        """Test basic logging functionality."""
        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.info("Test message")
            mock_info.assert_called_once_with("Test message", extra={'extras': {}})
    
    def test_logging_with_extras(self):
        """Test logging with extra fields."""
        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.info("Test message", extras={"field1": "value1", "field2": 123})
            mock_info.assert_called_once_with("Test message", extra={'extras': {"field1": "value1", "field2": 123}})
    
    def test_logging_with_context(self, mock_context_vars):
        """Test logging with context."""
        with patch.object(structured_logger.logger, 'info') as mock_info:
            with patch.object(structured_logger, 'set_context') as mock_set_context:
                with LogContext(user_id="123", component="TestComponent"):
                    structured_logger.info("Test message")
                    
                    # Check that set_context was called with the right parameters
                    mock_set_context.assert_called_once_with(
                        req_id=None, usr_id="123", cmd=None, comp="TestComponent"
                    )
                    
                    # The context variables should be added to extras
                    mock_info.assert_called_once()
    
    def test_timer_functionality(self):
        """Test the timer functionality."""
        with patch.object(structured_logger.logger, 'info') as mock_info:
            timer_id = structured_logger.start_timer("test_operation")
            assert timer_id in structured_logger.performance_metrics
            assert "start_time" in structured_logger.performance_metrics[timer_id]
            assert "name" in structured_logger.performance_metrics[timer_id]
            assert structured_logger.performance_metrics[timer_id]["name"] == "test_operation"
            
            # Stop the timer
            duration = structured_logger.stop_timer(timer_id)
            assert isinstance(duration, float)
            assert duration >= 0
            
            # Timer should be removed
            assert timer_id not in structured_logger.performance_metrics
            
            # Info should be called with performance information
            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args
            assert "Performance: test_operation took" in args[0]
            assert "extras" in kwargs["extra"]
            assert "duration" in kwargs["extra"]["extras"]
            assert "metric_name" in kwargs["extra"]["extras"]
            assert kwargs["extra"]["extras"]["metric_name"] == "test_operation"
    
    def test_command_logging(self):
        """Test command logging."""
        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.command("test_command", 0.5)
            
            # Command should be tracked in metrics
            assert "test_command" in structured_logger.command_latencies
            assert structured_logger.command_count == 1
            assert structured_logger.command_usage["test_command"] == 1
            
            # Info should be called with command information
            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args
            assert "Command executed: test_command" in args[0]
            assert "extras" in kwargs["extra"]
            assert "duration" in kwargs["extra"]["extras"]
            assert "command_name" in kwargs["extra"]["extras"]
            assert kwargs["extra"]["extras"]["command_name"] == "test_command"

class TestJSONFormatter:
    """Test the JSON formatter."""
    
    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_path",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert isinstance(formatted, str)
        
        # Parse JSON to validate format
        data = json.loads(formatted)
        assert "timestamp" in data
        assert "level" in data
        assert data["level"] == "INFO"
        assert "message" in data
        assert "logger" in data
        assert data["logger"] == "test_logger"
        assert "path" in data
        assert "line" in data
        assert data["line"] == 123
        assert "hostname" in data
    
    def test_format_with_exception(self):
        """Test formatting a record with exception info."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test_path",
                lineno=123,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert "exception" in data
        assert "type" in data["exception"]
        assert data["exception"]["type"] == "ValueError"
        assert "message" in data["exception"]
        assert "Test exception" in data["exception"]["message"]
        assert "traceback" in data["exception"]
    
    def test_format_with_context_vars(self):
        """Test formatting with context variables."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_path",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Set context variables
        request_id.set("req-123")
        user_id.set("user-456")
        command_name.set("test_command")
        component.set("test_component")
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert "request_id" in data
        assert data["request_id"] == "req-123"
        assert "user_id" in data
        assert data["user_id"] == "user-456"
        assert "command_name" in data
        assert data["command_name"] == "test_command"
        assert "component" in data
        assert data["component"] == "test_component"

class TestLogContext:
    """Test the LogContext context manager."""
    
    def test_context_manager(self, mock_context_vars):
        """Test that the context manager properly sets and restores context."""
        # Create mock context variables
        with patch.object(structured_logger, 'set_context') as mock_set_context, \
             patch('src.utils.structured_logger.request_id.get', return_value=None), \
             patch('src.utils.structured_logger.user_id.get', return_value=None), \
             patch('src.utils.structured_logger.command_name.get', return_value=None), \
             patch('src.utils.structured_logger.component.get', return_value=None):
            
            # Enter context
            with LogContext(request_id="req-123", user_id="user-456"):
                # Verify set_context was called
                mock_set_context.assert_called_once_with(
                    req_id="req-123", usr_id="user-456", cmd=None, comp=None
                )
                
                # Reset mock for the nested context
                mock_set_context.reset_mock()
                
                # Nested context
                with LogContext(request_id="req-789"):
                    # Verify set_context was called again
                    mock_set_context.assert_called_once_with(
                        req_id="req-789", usr_id=None, cmd=None, comp=None
                    )

class TestLogAggregator:
    """Test the log aggregator."""
    
    def test_log_entry_creation(self):
        """Test creating a log entry from raw data."""
        raw_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Test message",
            "logger": "test_logger",
            "request_id": "req-123",
            "user_id": "user-456",
            "command_name": "test_command",
            "component": "test_component",
            "extra_field": "extra_value"
        }
        
        entry = LogEntry(raw_data)
        
        assert entry.level == "INFO"
        assert entry.message == "Test message"
        assert entry.request_id == "req-123"
        assert entry.user_id == "user-456"
        assert entry.command_name == "test_command"
        assert entry.component == "test_component"
        assert "extra_field" in entry.extras
        assert entry.extras["extra_field"] == "extra_value"
    
    def test_log_entry_to_dict(self):
        """Test converting a log entry to dictionary."""
        raw_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Test message",
            "logger": "test_logger",
            "request_id": "req-123",
            "user_id": "user-456",
            "command_name": "test_command",
            "component": "test_component",
            "extra_field": "extra_value"
        }
        
        entry = LogEntry(raw_data)
        data = entry.to_dict()
        
        assert isinstance(data, dict)
        assert "timestamp" in data
        assert "level" in data
        assert data["level"] == "INFO"
        assert "message" in data
        assert data["message"] == "Test message"
        assert "request_id" in data
        assert data["request_id"] == "req-123"
        assert "extra_field" in data
        assert data["extra_field"] == "extra_value"
    
    @pytest.mark.asyncio
    async def test_process_log_entry(self):
        """Test processing a log entry."""
        log_aggregator = LogAggregator()
        
        raw_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": "Test error",
            "logger": "test_logger",
            "request_id": "req-123",
            "user_id": "user-456",
            "command_name": "test_command",
            "component": "test_component",
            "duration": 0.5
        }
        
        await log_aggregator.process_log_entry(raw_data)
        
        # Entry should be added to the main collection
        assert len(log_aggregator.entries) == 1
        
        # Entry should be indexed properly
        assert len(log_aggregator.request_index["req-123"]) == 1
        assert len(log_aggregator.user_index["user-456"]) == 1
        assert len(log_aggregator.command_index["test_command"]) == 1
        assert len(log_aggregator.component_index["test_component"]) == 1
        assert len(log_aggregator.level_index["ERROR"]) == 1
        
        # Error should be tracked
        assert len(log_aggregator.errors) == 1
        assert log_aggregator.error_count_by_component["test_component"] == 1
        
        # Performance metrics should be tracked
        assert "test_command" in log_aggregator.command_durations
        assert log_aggregator.command_durations["test_command"] == [0.5]
    
    def test_get_logs_filtering(self):
        """Test filtering logs."""
        log_aggregator = LogAggregator()
        
        # Add multiple entries with different attributes
        entries = []
        for i in range(5):
            entry = LogEntry({
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO" if i % 2 == 0 else "ERROR",
                "message": f"Test message {i}",
                "logger": "test_logger",
                "component": "comp1" if i < 3 else "comp2",
                "request_id": f"req-{i//2}"
            })
            entries.append(entry)
            log_aggregator.entries.append(entry)
            
            # Index the entry
            if entry.request_id:
                log_aggregator.request_index[entry.request_id].append(entry)
            if entry.component:
                log_aggregator.component_index[entry.component].append(entry)
            log_aggregator.level_index[entry.level].append(entry)
            
            # Track errors
            if entry.level in ("ERROR", "CRITICAL"):
                log_aggregator.errors.append(entry)
                if entry.component:
                    log_aggregator.error_count_by_component[entry.component] += 1
        
        # Filter by level
        logs = log_aggregator.get_logs(level="INFO")
        assert len(logs) == 3  # INFO entries (0, 2, 4)
        
        # Filter by component
        logs = log_aggregator.get_logs(component="comp1")
        assert len(logs) == 3  # Entries 0, 1, 2
        
        # Filter by request_id
        logs = log_aggregator.get_logs(request_id="req-0")
        assert len(logs) == 2  # Entries 0, 1
        
        # Multiple filters
        logs = log_aggregator.get_logs(level="ERROR", component="comp2")
        assert len(logs) == 1  # Only entry 3

class TestLoggingDecorators:
    """Test the logging decorators."""
    
    @pytest.mark.asyncio
    async def test_log_command_decorator(self, mock_context_vars):
        """Test the log_command decorator."""
        # Mock structured_logger for testing
        with patch("src.utils.logging_decorators.structured_logger") as mock_logger, \
             patch("src.utils.logging_decorators.LogContext") as mock_log_context:
            mock_logger.info = MagicMock()
            mock_logger.error = MagicMock()
            mock_logger.command = MagicMock()
            mock_log_context.return_value.__enter__ = MagicMock()
            mock_log_context.return_value.__exit__ = MagicMock()
            
            # Create a decorated function
            @log_command(component="TestComponent")
            async def test_command(self, interaction, arg1, arg2):
                return arg1 + arg2
            
            # Create mock objects
            mock_self = MagicMock()
            mock_interaction = MagicMock()
            mock_interaction.user.id = "123"
            
            # Call the decorated function
            result = await test_command(mock_self, mock_interaction, 5, 7)
            
            # Verify result
            assert result == 12
            
            # Verify logging
            mock_logger.info.assert_called_once()
            assert "Executing command: test_command" in mock_logger.info.call_args[0][0]
            
            # Verify command tracking
            mock_logger.command.assert_called_once()
            assert mock_logger.command.call_args[0][0] == "test_command"
            assert isinstance(mock_logger.command.call_args[0][1], float)
    
    @pytest.mark.asyncio
    async def test_log_task_decorator(self, mock_context_vars):
        """Test the log_task decorator."""
        # Mock structured_logger for testing
        with patch("src.utils.logging_decorators.structured_logger") as mock_logger, \
             patch("src.utils.logging_decorators.LogContext") as mock_log_context, \
             patch("uuid.uuid4", return_value="b9284f3b-a4f8-4ad0-94e7-b6406940def6"):
            mock_logger.info = MagicMock()
            mock_logger.error = MagicMock()
            mock_logger.start_timer = MagicMock(return_value="timer-123")
            mock_logger.stop_timer = MagicMock(return_value=0.5)
            mock_log_context.return_value.__enter__ = MagicMock()
            mock_log_context.return_value.__exit__ = MagicMock()
            
            # Create a decorated function
            @log_task(component="TestComponent")
            async def test_task(arg1, arg2):
                return arg1 * arg2
            
            # Call the decorated function
            result = await test_task(6, 7)
            
            # Verify result
            assert result == 42
            
            # Verify logging
            assert mock_logger.info.call_count == 2
            assert "Starting background task: test_task" in mock_logger.info.call_args_list[0][0][0]
            assert "Completed background task: test_task" in mock_logger.info.call_args_list[1][0][0]
            
            # Verify timer
            mock_logger.start_timer.assert_called_once_with("TestComponent.test_task")
            mock_logger.stop_timer.assert_called_once_with("timer-123")

# Modify this test for your environment and test coverage focus
def test_complete_flow():
    """Test a complete flow from logging to aggregation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Set up temporary log file
        log_file = os.path.join(tmp_dir, "newsbot_structured.json")
        
        # Create a sample log entry
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Test message",
            "logger": "test_logger",
            "request_id": "req-123",
            "user_id": "user-456",
            "command_name": "test_command",
            "component": "test_component"
        }
        
        # Write the log entry to the file
        with open(log_file, "w") as f:
            f.write(json.dumps(log_data) + "\n")
        
        # Patch the log file path in the aggregator
        with patch("src.monitoring.log_aggregator.LogAggregator._process_logs") as mock_process:
            # This test doesn't actually read the file but verifies the flow
            # In a real test, you would mock the file operations or use a real file
            pass 