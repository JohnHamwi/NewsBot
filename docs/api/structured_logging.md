# Structured Logging System

The NewsBot includes a comprehensive structured logging system designed to provide advanced tracking, monitoring, and debugging capabilities. This system enhances the bot's reliability and maintainability by providing detailed insights into its operation.

## Components

The structured logging system consists of several integrated components:

1. **Structured Logger** - Core component that provides JSON-formatted logs with rich context
2. **Log Aggregator** - Collects, processes, and analyzes log data
3. **Log API** - Discord commands for accessing and querying logs
4. **Logging Decorators** - Easy integration of structured logging in code

## Using the Structured Logger

The structured logger provides enhanced logging capabilities with context tracking and performance metrics.

```python
from src.utils.structured_logger import structured_logger, LogContext

# Basic logging
structured_logger.info("User joined the server", extras={
    'user_id': '123456789',
    'guild_id': '987654321'
})

# Logging with context
with LogContext(user_id='123456789', component='FetchCog'):
    structured_logger.info("Processing command")
    
    # Performance tracking
    timer_id = structured_logger.start_timer("fetch_operation")
    # ... perform operation ...
    duration = structured_logger.stop_timer(timer_id)
```

## Logging Decorators

The system provides decorators for easy integration of structured logging in your code:

```python
from src.utils.logging_decorators import log_command, log_method, log_function, log_task

class MyCog(commands.Cog):
    @log_command(component='MyCog')
    async def my_command(self, interaction, arg1, arg2):
        # This command is automatically logged with timing and error tracking
        pass
        
    @log_method()
    async def some_method(self, arg1):
        # This method is automatically logged with timing
        pass
        
@log_function(component='utilities')
async def my_function():
    # This function is automatically logged
    pass
    
@log_task(component='background_tasks')
async def my_background_task():
    # This background task is automatically logged with comprehensive tracking
    pass
```

## Log API Commands

The system provides Discord slash commands for accessing logs and metrics:

| Command | Description |
|---------|-------------|
| `/logs` | View recent logs with filtering options |
| `/error_summary` | View a summary of recent errors |
| `/performance` | View performance metrics for commands |
| `/user_activity` | View activity logs for a specific user |

### Example: Viewing Logs

```
/logs level:ERROR component:FetchCog hours:24 limit:10
```

This will display the last 10 ERROR-level logs from the FetchCog component in the last 24 hours.

## Log Aggregator

The log aggregator collects and processes logs from the structured logging system. It provides:

- Log storage and indexing
- Filtering and querying capabilities
- Error tracking and notification
- Performance metric calculation

### Key Features

- **JSON-formatted logs** for better parsing and analysis
- **Request correlation IDs** for tracing requests across components
- **User context tracking** for better debugging user-specific issues
- **Component-based logging** for better organization
- **Performance metrics** for identifying bottlenecks
- **Error tracking** for quick identification of issues

## Integration with External Systems

The structured logging system outputs JSON-formatted logs that can be easily integrated with external monitoring systems:

- **Log aggregation tools** like ELK Stack (Elasticsearch, Logstash, Kibana)
- **Monitoring services** like Datadog or New Relic
- **Custom dashboards** for real-time monitoring

## Best Practices

1. **Use components consistently** - Always specify the component in logs for better organization
2. **Add context** - Include relevant IDs (user, guild, channel) in log extras
3. **Use decorators** - Prefer decorators for consistent logging across similar functions
4. **Log at appropriate levels** - Use DEBUG for detailed tracking, INFO for normal operations, WARNING for potential issues, ERROR for failures
5. **Include structured data** - Use the extras parameter to include structured data for better analysis 