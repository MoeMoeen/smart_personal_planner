"""
Structured logging infrastructure for the Smart Personal Planner.

Provides consistent, structured logging across all components with context
tracking, performance metrics, and debugging capabilities.
"""

import logging
import time
import json
from typing import Any, Dict, Optional
from contextlib import contextmanager
from functools import wraps

# Configure basic structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_planning_logger(name: str = __name__):
    """Get a logger instance for planning operations."""
    return logging.getLogger(name)

def log_structured(logger: logging.Logger, level: str, message: str, **kwargs):
    """Log a structured message with JSON-serializable data."""
    log_data = {"event": message, **kwargs}
    log_message = json.dumps(log_data, default=str, sort_keys=True)
    getattr(logger, level)(log_message)

class PlanningLogger:
    """Centralized logging for planning operations with context tracking."""
    
    def __init__(self, component: str, session_id: Optional[str] = None, user_id: Optional[str] = None):
        self.logger = get_planning_logger(component)
        self.component = component
        self.session_id = session_id
        self.user_id = user_id
        self._context = {
            "component": component,
            "session_id": session_id,
            "user_id": user_id
        }
    
    def _log(self, level: str, event: str, **kwargs):
        """Internal logging method that adds context."""
        log_data = {**self._context, **kwargs}
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        log_structured(self.logger, level, event, **log_data)
    
    def info(self, event: str, **kwargs):
        self._log("info", event, **kwargs)
    
    def error(self, event: str, **kwargs):
        self._log("error", event, **kwargs)
    
    def warning(self, event: str, **kwargs):
        self._log("warning", event, **kwargs)
    
    def debug(self, event: str, **kwargs):
        self._log("debug", event, **kwargs)

@contextmanager
def log_operation(logger: PlanningLogger, operation: str, **context):
    """Context manager for logging operation start/end with timing."""
    start_time = time.time()
    operation_id = f"{operation}_{int(start_time * 1000)}"
    
    logger.info("operation_start", 
        operation=operation,
        operation_id=operation_id,
        **context
    )
    
    try:
        yield operation_id
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info("operation_complete",
            operation=operation,
            operation_id=operation_id,
            duration_ms=duration_ms,
            status="success",
            **context
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("operation_failed",
            operation=operation, 
            operation_id=operation_id,
            duration_ms=duration_ms,
            error=str(e),
            error_type=type(e).__name__,
            **context
        )
        raise

def log_llm_call(func):
    """Decorator for logging LLM calls with token usage and cost tracking."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_planning_logger(f"{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        # Extract context from args/kwargs if available
        context = {}
        if hasattr(args[0], '__class__'):
            context["tool"] = args[0].__class__.__name__
        
        log_structured(logger, "info", "llm_call_start", 
                      function=func.__name__, **context)
        
        try:
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract metrics from result if available
            metrics = {}
            if hasattr(result, 'confidence'):
                metrics["confidence"] = result.confidence
            if hasattr(result, 'data') and isinstance(result.data, dict):
                if 'token_usage' in result.data:
                    metrics.update(result.data['token_usage'])
            
            log_structured(logger, "info", "llm_call_complete",
                          function=func.__name__,
                          duration_ms=duration_ms,
                          status="success",
                          **context,
                          **metrics)
            
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_structured(logger, "error", "llm_call_failed",
                          function=func.__name__,
                          duration_ms=duration_ms,
                          error=str(e),
                          error_type=type(e).__name__,
                          **context)
            raise
    
    return wrapper

class TokenUsageTracker:
    """Track token usage and costs across LLM calls."""
    
    def __init__(self):
        self.total_tokens = 0
        self.total_calls = 0
        self.estimated_cost = 0.0
        self.call_history = []
    
    def record_call(self, tool_name: str, tokens: int, cost: float = 0.0):
        """Record an LLM call with token usage."""
        self.total_tokens += tokens
        self.total_calls += 1
        self.estimated_cost += cost
        
        call_record = {
            "tool": tool_name,
            "tokens": tokens,
            "cost": cost,
            "timestamp": time.time()
        }
        self.call_history.append(call_record)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        return {
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
            "estimated_cost": self.estimated_cost,
            "avg_tokens_per_call": self.total_tokens / max(self.total_calls, 1)
        }