"""Logging setup for the application using Loguru and Rich."""

from loguru import logger
from rich.logging import RichHandler


def setup_logging() -> None:
    """Configures Loguru with console (Rich) and file handlers."""
    logger.remove()  # Remove default handler

    # Console Handler (Rich)
    logger.add(
        RichHandler(
            show_path=False,  # As per spec example
            omit_repeated_times=False, # As per spec example
            show_level=True, # As per spec example
            show_time=True, # As per spec example
            rich_tracebacks=True, # As per spec example
            tracebacks_show_locals=True,
            markup=True # Enable Rich markup in log messages
        ),
        level="INFO",
        format="{message}",  # RichHandler mostly controls formatting
        colorize=True # Ensure colorized output even if stdout is not a TTY (e.g. in some IDEs)
    )

    # File Handler
    logger.add(
        "app.log",
        level="DEBUG",
        rotation="10 MB",  # Rotate when file reaches 10 MB (as per spec)
        retention="7 days",  # Keep logs for 7 days (as per spec)
        compression="zip",  # Compress rotated files (as per spec)
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}", # As per spec
        enqueue=True,  # For asynchronous logging (as per spec)
        backtrace=True,  # Better tracebacks in files (as per spec)
        diagnose=True,  # Extended diagnosis for errors (as per spec)
        # serialize=True, # Consider if JSON logs are needed for external processing
    )

    logger.info("Logging configured. Console: INFO, File: DEBUG at app.log") 