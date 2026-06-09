"""Structured logging configuration with sensitive data masking."""

import logging
import re
import sys

import structlog
from structlog.types import EventDict, WrappedLogger

SENSITIVE_KEY_NAMES = {
    "api_key",
    "apikey",
    "password",
    "passwd",
    "token",
    "secret",
    "authorization",
}

SENSITIVE_PATTERNS = [
    (re.compile(r"(sk-[a-zA-Z0-9]{8})[a-zA-Z0-9]+", re.IGNORECASE), r"\1***"),
]


def mask_sensitive_data(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Mask sensitive data in log events."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            if key.lower() in SENSITIVE_KEY_NAMES:
                event_dict[key] = "***MASKED***"
            else:
                for pattern, replacement in SENSITIVE_PATTERNS:
                    event_dict[key] = pattern.sub(replacement, event_dict[key])
    return event_dict


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging with structlog."""
    log_level = logging.DEBUG if debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            mask_sensitive_data,
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a named logger instance."""
    return structlog.get_logger(name)
