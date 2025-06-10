# Task Manager API

The Task Manager module provides robust management of background tasks with automatic error recovery, graceful shutdown, and detailed monitoring.

## Features

- Automatic task recovery with configurable retry policies
- Exponential backoff for failed tasks
- Graceful shutdown of long-running tasks
- Task statistics and monitoring
- Rate limiting for task restarts
- Error reporting and logging

## Usage

### Basic Task Management

```python
import asyncio
from src.utils.task_manager import task_manager

# Define your async task
async def my_background_task(arg1, arg2):
    while True:
        print(f"Processing {arg1} and {arg2}")
        await asyncio.sleep(60)

# Start the task with automatic restart on failure
await task_manager.start_task(
    name="my_task",
    coro=my_background_task,
    "value1", "value2",  # Args for my_background_task
    restart_on_failure=True
)

# Check if task is running
is_running = task_manager.is_running("my_task")

# Stop the task gracefully
await task_manager.stop_task("my_task")

# Get task statistics
stats = task_manager.get_task_stats()
```

### Setting Bot Instance for Error Reporting

```python
from src.utils.task_manager import set_bot_instance

# Set bot instance for error reporting in tasks
set_bot_instance(bot)
```

### Error Handling in Tasks

Tasks automatically handle errors with these behaviors:

1. Errors are logged with detailed context
2. If `restart_on_failure` is enabled, the task will restart
3. Exponential backoff is applied to avoid rapid restarts
4. After reaching `max_restarts` within the `restart_window`, the task will terminate
5. All errors are reported to Discord if a bot instance is provided

### Shutting Down Tasks

```python
# Stop all running tasks gracefully
await task_manager.stop_all_tasks()
```

## Task Manager Configuration

The `TaskManager` class has several configurable properties:

| Property | Default | Description |
| --- | --- | --- |
| `max_restarts` | 5 | Maximum number of restarts allowed in the restart window |
| `restart_window` | 60 | Time window in seconds for counting restarts |
| `backoff_factor` | 1.5 | Exponential backoff factor between retries |

Example of custom configuration:

```python
from src.utils.task_manager import TaskManager

# Create a custom task manager
custom_manager = TaskManager()
custom_manager.max_restarts = 3
custom_manager.restart_window = 300  # 5 minutes
custom_manager.backoff_factor = 2.0

# Set bot instance for error reporting
custom_manager.bot = bot
```

## API Reference

### `TaskManager` Class

#### `.start_task(name: str, coro: Callable, *args, restart_on_failure: bool = True, **kwargs) -> None`

Start a background task with error recovery.

- **Parameters:**
  - `name`: Unique name for the task
  - `coro`: Coroutine function to run as a task
  - `*args`: Arguments to pass to the coroutine
  - `restart_on_failure`: Whether to restart the task on failure
  - `**kwargs`: Keyword arguments to pass to the coroutine

#### `.stop_task(name: str, timeout: float = 5.0) -> bool`

Stop a running task gracefully.

- **Parameters:**
  - `name`: Task name
  - `timeout`: Maximum time to wait for the task to stop
- **Returns:**
  - `True` if the task was stopped, `False` otherwise

#### `.stop_all_tasks(timeout: float = 5.0) -> None`

Stop all running tasks gracefully.

- **Parameters:**
  - `timeout`: Maximum time to wait for each task to stop

#### `.get_task(name: str) -> Optional[asyncio.Task]`

Get a task by name.

- **Parameters:**
  - `name`: Task name
- **Returns:**
  - Task object or `None` if not found

#### `.is_running(name: str) -> bool`

Check if a task is running.

- **Parameters:**
  - `name`: Task name
- **Returns:**
  - `True` if the task is running, `False` otherwise

#### `.get_task_stats() -> Dict[str, Dict[str, Any]]`

Get statistics about all tasks.

- **Returns:**
  - Dictionary of task statistics

### Helper Functions

#### `set_bot_instance(bot)`

Set the bot instance for the global task manager.

- **Parameters:**
  - `bot`: Bot instance

## Global Instance

A global `task_manager` instance is provided for convenience. This can be used throughout the application without creating new instances. 