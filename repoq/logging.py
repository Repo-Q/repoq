"""Logging configuration using Rich for beautiful console output.

This module configures Python's logging system with Rich handlers for:
- Colored, formatted log messages
- Pretty tracebacks
- Verbosity level control (WARNING/INFO/DEBUG)
"""

from __future__ import annotations

import logging

from rich.logging import RichHandler


def setup_logging(verbosity: int = 0) -> None:
    """Configure logging with Rich handler and verbosity level.

    Args:
        verbosity: Verbosity count from CLI:
            - 0: WARNING level (default)
            - 1: INFO level (-v)
            - 2+: DEBUG level (-vv)

    Example:
        >>> setup_logging(1)  # Enable INFO logging
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("This message will appear")
    """
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
