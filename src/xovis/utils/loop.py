"""
Xovis SDK - Event Loop Utilities

Provides utility functions for configuring the optimal asyncio event loop policy
across different operating systems. This is critical for the Data Plane's
high-throughput requirements, ensuring `uvloop` is utilized on Linux/macOS
and `ProactorEventLoop` on Windows.
"""

import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


def setup_optimal_loop():
    """
    Configures the most performant asyncio event loop policy for the current platform.

    On Windows, it ensures the use of `ProactorEventLoop`, which is required for
    high-performance TCP and subprocess operations. On Linux and macOS, it
    attempts to load and set `uvloop` as the global event loop policy.

    Raises:
        ImportError: Silently handled if `uvloop` or Windows-specific policies
            are unavailable.
    """
    if sys.platform == "win32":
        if sys.version_info < (3, 12):
            try:
                from asyncio import WindowsProactorEventLoopPolicy

                asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
                logger.debug("Configured WindowsProactorEventLoopPolicy")
            except ImportError:
                pass
        else:
            logger.debug("Python 3.12+ detected on Windows; using default ProactorEventLoop")
    else:
        try:
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logger.debug("Configured uvloop.EventLoopPolicy")
        except ImportError:
            logger.debug("uvloop not found, using default SelectorEventLoop")
