# app/cognitive/utils/llm_utils.py
"""
Decorator utilities for LLM robustness: retry, timing, logging, and cost tracking.
"""
import time
import logging
from functools import wraps
import random

def llm_retry_and_log(max_retries=3, base_delay=1.0, logger_name="llm_call"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name)
            attempt = 0
            start_time = time.time()
            while attempt < max_retries:
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    logger.info({
                        "event": "llm_call_success",
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "elapsed_sec": elapsed
                    })
                    return result
                except Exception as e:
                    attempt += 1
                    logger.warning({
                        "event": "llm_call_retry",
                        "function": func.__name__,
                        "attempt": attempt,
                        "error": str(e)
                    })
                    if attempt >= max_retries:
                        logger.error({
                            "event": "llm_call_failure",
                            "function": func.__name__,
                            "error": str(e)
                        })
                        raise
                    # Exponential backoff with jitter
                    time.sleep(base_delay * (2 ** (attempt-1)) + random.uniform(0, 0.25))
        return wrapper
    return decorator
