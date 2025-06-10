# NewsBot Logging Tools

This directory contains scripts for working with the structured logging system without having to run the Discord bot.

## Available Scripts

### 1. Demo Logging (`demo_logging.py`)

This script demonstrates all the features of the structured logging system programmatically.

**Usage:**
```bash
./demo_logging.py
```

**Features Demonstrated:**
- Basic logging at different levels (debug, info, warning, error)
- Context management with `LogContext`
- Performance tracking with timers
- Error handling and tracking
- Async task logging
- Log aggregation

### 2. View Logs (`view_logs.py`)

A command-line tool for viewing and analyzing structured logs with filtering options.

**Usage:**
```bash
./view_logs.py [options]
```

**Options:**
- `--file PATH` - Path to the log file (default: logs/newsbot_structured.json)
- `--level {debug,info,warning,error,critical}` - Filter by log level
- `--component COMPONENT` - Filter by component
- `--user USER_ID` - Filter by user ID
- `--hours HOURS` - Only show logs from the last N hours
- `--limit N` - Maximum number of logs to display (default: 20)
- `--verbose, -v` - Show detailed log information
- `--errors, -e` - Show error summary
- `--performance, -p` - Show performance metrics

**Examples:**
```bash
# Show last 10 logs with verbose output
./view_logs.py --limit 10 --verbose

# Show only error logs
./view_logs.py --level error

# Show logs from a specific component
./view_logs.py --component FetchCog

# Show error summary and performance metrics
./view_logs.py --errors --performance
```

### 3. Log Report (`log_report.py`)

Generates PDF reports from structured logs for easy visualization and sharing.

**Prerequisites:**
```bash
pip install matplotlib fpdf
```

**Usage:**
```bash
./log_report.py [options]
```

**Options:**
- `--file PATH` - Path to the log file (default: logs/newsbot_structured.json)
- `--output FILENAME` - Output PDF file name (default: log_report.pdf)
- `--title TITLE` - Report title (default: "NewsBot Log Report")
- `--level {debug,info,warning,error,critical}` - Filter by log level
- `--component COMPONENT` - Filter by component
- `--hours HOURS` - Only include logs from the last N hours

**Examples:**
```bash
# Generate a default report
./log_report.py

# Generate a report for a specific component
./log_report.py --component Demo --output demo_report.pdf

# Generate a report for errors in the last 24 hours
./log_report.py --level error --hours 24 --output error_report.pdf
```

## Structured Logging Features

The NewsBot structured logging system provides:

1. **Rich Contextual Information**:
   - Component tracking
   - User activity tracking
   - Request correlation with unique IDs
   - Method/function/task tracking

2. **Performance Metrics**:
   - Command execution time tracking
   - Method duration measurement
   - Operation timing

3. **Error Handling**:
   - Detailed exception information
   - Stack traces
   - Error categorization by component

4. **Log Aggregation**:
   - Recent logs retrieval
   - Error summaries
   - Performance metrics aggregation
   - User activity tracking

5. **JSON Formatting**:
   - Machine-readable logs
   - Structured fields for easy parsing
   - Consistent timestamp formatting

## Adding Structured Logging to Your Code

To add structured logging to your own code, use the following patterns:

```python
# Basic logging
from src.utils.structured_logger import structured_logger
structured_logger.info("Message", extras={"key": "value"})

# Logging with context
from src.utils.structured_logger import LogContext
with LogContext(user_id="123", component="MyComponent"):
    structured_logger.info("Action performed")

# Logging decorators
from src.utils.logging_decorators import log_method, log_function, log_task

@log_method(component="MyComponent")
def my_method(self, arg1, arg2):
    # Method implementation
    pass

@log_function(component="MyComponent")
def my_function(arg1, arg2):
    # Function implementation
    pass

@log_task(component="MyComponent")
async def my_task():
    # Async task implementation
    pass
``` 