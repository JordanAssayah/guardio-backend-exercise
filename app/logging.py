"""
Centralized logging configuration using loguru.
"""
from __future__ import annotations

import sys
from typing import Any

from loguru import logger

# Remove default handler and add custom one with better format
logger.remove()

logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    level="DEBUG",
    colorize=True,
)


def get_logger(name: str = __name__) -> Any:
    """
    Get a logger bound to a specific module name.
    
    Usage:
        from app.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Hello from this module")
    """
    return logger.bind(name=name)

