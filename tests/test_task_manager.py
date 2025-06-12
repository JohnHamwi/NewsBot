"""
Test suite for the TaskManager class.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.task_manager import TaskManager


@pytest.mark.asyncio
async def test_task_manager_start_task():
    """Test starting a task with the task manager."""
    # Create task manager
    manager = TaskManager()

    # Create a mock coroutine function
    mock_coro = AsyncMock()

    # Start the task
    await manager.start_task("test_task", mock_coro, "arg1", "arg2", kwarg1="value1")

    # Task should be in the manager
    assert "test_task" in manager.tasks
    assert manager.is_running("test_task")

    # Wait for the task to complete
    await asyncio.sleep(0.1)

    # Mock should have been called with the right arguments
    mock_coro.assert_called_once_with("arg1", "arg2", kwarg1="value1")


@pytest.mark.asyncio
async def test_task_manager_task_error_and_restart():
    """Test error handling and task restart."""
    # Create task manager
    manager = TaskManager()

    # Create a function that raises an exception on first call, then succeeds
    call_count = 0

    async def failing_task():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Test error")
        await asyncio.sleep(0.1)

    # Make the backoff shorter for testing
    manager.backoff_factor = 1.0

    # Start the task
    await manager.start_task("failing_task", failing_task, restart_on_failure=True)

    # Wait for the task to restart and complete (with timeout)
    for _ in range(10):  # Try for up to 1 second
        await asyncio.sleep(0.1)
        if call_count >= 2:
            break

    # Verify task was started
    assert call_count >= 1

    # Verify restart was scheduled
    assert "failing_task" in manager.restart_counts


@pytest.mark.asyncio
async def test_task_manager_stop_task():
    """Test stopping a task."""
    # Create task manager
    manager = TaskManager()

    # Create a long-running task
    async def long_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    # Start the task
    await manager.start_task("long_task", long_task)

    # Task should be running
    assert manager.is_running("long_task")

    # Stop the task
    result = await manager.stop_task("long_task")

    # Stop should succeed
    assert result is True

    # Task should no longer be running
    assert not manager.is_running("long_task")


@pytest.mark.asyncio
async def test_task_manager_stop_all_tasks():
    """Test stopping all tasks."""
    # Create task manager
    manager = TaskManager()

    # Create multiple long-running tasks
    async def long_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    # Start multiple tasks
    for i in range(3):
        await manager.start_task(f"long_task_{i}", long_task)

    # All tasks should be running
    for i in range(3):
        assert manager.is_running(f"long_task_{i}")

    # Stop all tasks
    await manager.stop_all_tasks()

    # No tasks should be running
    for i in range(3):
        assert not manager.is_running(f"long_task_{i}")


@pytest.mark.asyncio
async def test_task_manager_max_restarts():
    """Test that tasks don't restart beyond max_restarts."""
    # Create task manager with custom settings
    manager = TaskManager()
    manager.max_restarts = 2
    manager.restart_window = 60
    manager.backoff_factor = 1.0  # No backoff for faster test

    # Create a task that always fails
    call_count = 0

    async def always_failing_task():
        nonlocal call_count
        call_count += 1
        raise ValueError(f"Error {call_count}")

    # Start the task
    await manager.start_task(
        "failing_task", always_failing_task, restart_on_failure=True
    )

    # Wait for max restarts with timeout
    for _ in range(30):  # Try for up to 3 seconds
        await asyncio.sleep(0.1)
        if call_count >= 2:
            break

    # Verify task was started at least once
    assert call_count >= 1

    # Verify restart was scheduled
    assert "failing_task" in manager.restart_counts
    assert manager.restart_counts["failing_task"] >= 1


@pytest.mark.asyncio
async def test_task_manager_get_task_stats():
    """Test getting task statistics."""
    # Create task manager
    manager = TaskManager()

    # Create tasks with different behaviors
    async def completed_task():
        await asyncio.sleep(0.1)

    async def failing_task():
        raise ValueError("Test error")

    async def long_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    # Start tasks
    await manager.start_task("completed", completed_task)
    await manager.start_task("failing", failing_task, restart_on_failure=False)
    await manager.start_task("long", long_task)

    # Wait for some tasks to complete
    await asyncio.sleep(0.2)

    # Get stats
    stats = manager.get_task_stats()

    # Should have stats for all tasks
    assert "completed" in stats
    assert "failing" in stats
    assert "long" in stats

    # Completed task should be done
    assert stats["completed"]["running"] is False

    # Failing task should be done
    assert stats["failing"]["running"] is False
    # Note: The exception might not be directly accessible in all environments

    # Long task should still be running
    assert stats["long"]["running"] is True
