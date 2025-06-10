"""
Tests for the logging decorators module.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import inspect

from src.utils.logging_decorators import (
    log_command,
    log_method,
    log_function,
    log_task
)


class TestDecorators:
    """Tests for the logging decorators."""
    
    @pytest.mark.asyncio
    async def test_log_function_decorator(self):
        """Test the log_function decorator."""
        with patch('src.utils.logging_decorators.structured_logger') as mock_logger:
            mock_logger.info = MagicMock()
            mock_logger.error = MagicMock()
            mock_logger.start_timer = MagicMock(return_value="timer-123")
            mock_logger.stop_timer = MagicMock(return_value=0.5)
            
            # Create decorated function
            @log_function(component="TestComponent")
            def test_function(a, b):
                """Test function."""
                return a + b
            
            # Call the function
            result = test_function(3, 4)
            
            # Check result
            assert result == 7
            
            # Verify timer was started and stopped
            mock_logger.start_timer.assert_called_once_with("TestComponent.test_function")
            mock_logger.stop_timer.assert_called_once_with("timer-123")
    
    @pytest.mark.asyncio
    async def test_log_method_decorator(self):
        """Test the log_method decorator."""
        with patch('src.utils.logging_decorators.structured_logger') as mock_logger:
            mock_logger.debug = MagicMock()
            mock_logger.error = MagicMock()
            mock_logger.start_timer = MagicMock(return_value="timer-123")
            mock_logger.stop_timer = MagicMock(return_value=0.5)
            
            # Create a class with decorated method
            class TestClass:
                @log_method(component="TestComponent")
                def test_method(self, a, b):
                    """Test method."""
                    return a * b
            
            # Create instance and call method
            instance = TestClass()
            result = instance.test_method(5, 6)
            
            # Check result
            assert result == 30
            
            # Verify timer was started and stopped
            mock_logger.start_timer.assert_called_once_with("TestComponent.test_method")
            mock_logger.debug.assert_called_once()
            mock_logger.stop_timer.assert_called_once_with("timer-123")
    
    @pytest.mark.asyncio
    async def test_log_function_with_exception(self):
        """Test the log_function decorator with an exception."""
        with patch('src.utils.logging_decorators.structured_logger') as mock_logger:
            mock_logger.start_timer = MagicMock(return_value="timer-123")
            mock_logger.stop_timer = MagicMock(return_value=0.5)
            mock_logger.error = MagicMock()
            
            # Create decorated function that raises an exception
            @log_function(component="TestComponent")
            def failing_function():
                """Function that raises an exception."""
                raise ValueError("Test exception")
            
            # Call the function and expect an exception
            with pytest.raises(ValueError):
                failing_function()
            
            # Verify timer was started and stopped even with exception
            mock_logger.start_timer.assert_called_once_with("TestComponent.failing_function")
            mock_logger.error.assert_called_once()
            mock_logger.stop_timer.assert_called_once_with("timer-123")
    
    @pytest.mark.asyncio
    async def test_async_log_function_decorator(self):
        """Test the log_function decorator with an async function."""
        with patch('src.utils.logging_decorators.structured_logger') as mock_logger:
            mock_logger.start_timer = MagicMock(return_value="timer-123")
            mock_logger.stop_timer = MagicMock(return_value=0.5)
            
            # Create decorated async function
            @log_function(component="TestComponent")
            async def test_async_function(a, b):
                """Test async function."""
                await asyncio.sleep(0.01)  # Small delay
                return a + b
            
            # Call the function
            result = await test_async_function(3, 4)
            
            # Check result
            assert result == 7
            
            # Verify timer was started and stopped
            mock_logger.start_timer.assert_called_once_with("TestComponent.test_async_function")
            mock_logger.stop_timer.assert_called_once_with("timer-123")
    
    def test_decorator_preserves_metadata(self):
        """Test that the decorators preserve function metadata."""
        # Original function with docstring
        def original_function(a, b):
            """This is a test function."""
            return a + b
        
        # Apply decorator
        decorated = log_function(component="TestComponent")(original_function)
        
        # Check that metadata is preserved
        assert decorated.__name__ == "original_function"
        assert decorated.__doc__ == "This is a test function."
        assert inspect.signature(decorated) == inspect.signature(original_function)
    
    @pytest.mark.asyncio
    async def test_log_command_decorator(self):
        """Test the log_command decorator."""
        with patch('src.utils.logging_decorators.structured_logger') as mock_logger:
            mock_logger.info = MagicMock()
            mock_logger.error = MagicMock()
            mock_logger.command = MagicMock()
            
            # Create a class with decorated command
            class TestCog:
                @log_command(component="TestComponent")
                async def test_command(self, interaction, arg1, arg2):
                    """Test command."""
                    return arg1 + arg2
            
            # Create mock objects
            instance = TestCog()
            interaction = MagicMock()
            interaction.user = MagicMock()
            interaction.user.id = "123456789"
            
            # Call the command
            result = await instance.test_command(interaction, 5, 10)
            
            # Check result
            assert result == 15
            
            # Verify logging
            mock_logger.info.assert_called_once()
            assert "Executing command: test_command" in mock_logger.info.call_args[0][0]
            mock_logger.command.assert_called_once_with("test_command", ANY)
    
    @pytest.mark.asyncio
    async def test_log_task_decorator(self):
        """Test the log_task decorator."""
        with patch('src.utils.logging_decorators.structured_logger') as mock_logger:
            mock_logger.info = MagicMock()
            mock_logger.error = MagicMock()
            mock_logger.start_timer = MagicMock(return_value="timer-123")
            mock_logger.stop_timer = MagicMock(return_value=0.5)
            
            # Create decorated task function
            @log_task(component="TestComponent")
            async def test_task(arg1, arg2):
                """Test task."""
                await asyncio.sleep(0.01)  # Small delay
                return arg1 * arg2
            
            # Call the function
            result = await test_task(6, 7)
            
            # Check result
            assert result == 42
            
            # Verify logging
            assert mock_logger.info.call_count >= 2
            assert "Starting background task: test_task" in mock_logger.info.call_args_list[0][0][0]
            assert "Completed background task: test_task" in mock_logger.info.call_args_list[-1][0][0]
            
            # Verify timer
            mock_logger.start_timer.assert_called_once_with("TestComponent.test_task")
            mock_logger.stop_timer.assert_called_once_with("timer-123") 