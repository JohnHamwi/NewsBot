"""
Enhanced Debug Logger for NewsBot
Provides comprehensive logging with context tracking and performance monitoring.
"""

import json
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps

from src.utils.base_logger import base_logger


class DebugLogger:
    """Enhanced debugging logger with context tracking."""
    
    def __init__(self):
        self.logger = base_logger
        self.context_stack = []
        self.performance_data = {}
        
    def push_context(self, context: str, **kwargs):
        """Push a new context onto the stack for nested operations."""
        ctx = {
            'name': context,
            'timestamp': datetime.now().isoformat(),
            'data': kwargs
        }
        self.context_stack.append(ctx)
        self._log_with_context('DEBUG', f"→ Entering {context}", kwargs)
        
    def pop_context(self, success: bool = True, **kwargs):
        """Pop the current context from the stack."""
        if not self.context_stack:
            return
            
        ctx = self.context_stack.pop()
        status = "✅" if success else "❌"
        self._log_with_context('DEBUG', f"← Exiting {ctx['name']} {status}", kwargs)
        
    def _log_with_context(self, level: str, message: str, extra_data: Dict = None):
        """Log with full context information."""
        if not self.context_stack:
            getattr(self.logger, level.lower())(message)
            return
            
        # Build context path
        context_path = " → ".join([ctx['name'] for ctx in self.context_stack])
        
        # Prepare extra data
        if extra_data:
            data_str = json.dumps(extra_data, default=str, indent=2)
            full_message = f"[{context_path}] {message}\nData: {data_str}"
        else:
            full_message = f"[{context_path}] {message}"
            
        getattr(self.logger, level.lower())(full_message)
        
    def debug(self, message: str, **kwargs):
        """Debug level logging with context."""
        self._log_with_context('DEBUG', message, kwargs)
        
    def info(self, message: str, **kwargs):
        """Info level logging with context."""
        self._log_with_context('INFO', message, kwargs)
        
    def warning(self, message: str, **kwargs):
        """Warning level logging with context."""
        self._log_with_context('WARNING', message, kwargs)
        
    def error(self, message: str, error: Exception = None, **kwargs):
        """Error level logging with context and stack trace."""
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
            kwargs['traceback'] = traceback.format_exc()
            
        self._log_with_context('ERROR', message, kwargs)


# Global debug logger instance
debug_logger = DebugLogger()


def debug_context(context_name: str):
    """Decorator to automatically manage debug context."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            debug_logger.push_context(context_name, function=func.__name__, args_count=len(args))
            try:
                result = await func(*args, **kwargs)
                debug_logger.pop_context(success=True, result_type=type(result).__name__)
                return result
            except Exception as e:
                debug_logger.pop_context(success=False, error=str(e))
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            debug_logger.push_context(context_name, function=func.__name__, args_count=len(args))
            try:
                result = func(*args, **kwargs)
                debug_logger.pop_context(success=True, result_type=type(result).__name__)
                return result
            except Exception as e:
                debug_logger.pop_context(success=False, error=str(e))
                raise
                
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


def performance_monitor(operation_name: str):
    """Decorator to monitor performance of operations."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                debug_logger.info(f"⏱️ {operation_name} completed", duration_seconds=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                debug_logger.error(f"⏱️ {operation_name} failed", error=e, duration_seconds=duration)
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                debug_logger.info(f"⏱️ {operation_name} completed", duration_seconds=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                debug_logger.error(f"⏱️ {operation_name} failed", error=e, duration_seconds=duration)
                raise
                
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator 