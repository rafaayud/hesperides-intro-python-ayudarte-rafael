"""
Custom decorators for the trading domain.
"""
import functools
import logging
import time
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def timed_async(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that measures the time it takes an async function to execute.

    Usage:
        @timed_async
        async def fetch_candles(...):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"{func.__name__} completed in {elapsed_ms:.2f}ms")
    return wrapper


def timed(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that measures the time it takes a sync function to execute.

    Usage:
        @timed
        def generate_signal(...):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"{func.__name__} completed in {elapsed_ms:.2f}ms")
    return wrapper
