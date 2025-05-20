# Loguru Usage Specification

This document details how the `loguru` library will be used for logging within the application.

## Purpose

`loguru` will provide a flexible and powerful logging solution, outputting log messages to both the console (enhanced by `rich`) and to disk files.

## Key Features and Configuration

1.  **Ease of Use:** `loguru` is known for its simple API.

2.  **Console Logging (via Rich):**
    *   Logs to `sys.stderr` (or `sys.stdout`) will be configured.
    *   Integration with `rich.logging.RichHandler` will be used for formatted, colorful console output.
    *   Log level for console output should be configurable (e.g., `INFO` by default).

3.  **File Logging:**
    *   Logs will be written to a file (e.g., `app.log`).
    *   Log level for file output should be configurable and typically more verbose (e.g., `DEBUG` by default) to capture detailed information for troubleshooting.
    *   **Rotation:** Log files should rotate based on size (e.g., every 10 MB) and/or time (e.g., daily) to prevent them from growing indefinitely.
    *   **Retention:** Old log files should be kept for a certain period (e.g., 7 days) or a certain number of files should be retained.
    *   **Compression:** Rotated log files can be compressed (e.g., `.zip` or `.gz`) to save disk space.

4.  **Structured Logging:** `loguru` makes it easy to include extra data in log records, which can be useful for context.

5.  **Exception Logging:** Automatic, improved traceback capturing for exceptions.

## Example Configuration

```python
from loguru import logger
from rich.logging import RichHandler
import sys

# Conceptual configuration
# In actual app, this would be driven by AppConfig
CONSOLE_LOG_LEVEL = "INFO"
FILE_LOG_LEVEL = "DEBUG"
LOG_FILE_PATH = "app.log"

def setup_logging():
    logger.remove() # Remove default handler

    # Console Handler (Rich)
    logger.add(
        RichHandler(
            show_path=False, # Don't show module path for cleaner logs
            omit_repeated_times=False,
            show_level=True,
            show_time=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True # Useful for debugging
        ),
        level=CONSOLE_LOG_LEVEL,
        format="{message}" # RichHandler mostly controls formatting
    )

    # File Handler
    logger.add(
        LOG_FILE_PATH,
        level=FILE_LOG_LEVEL,
        rotation="10 MB",  # Rotate when file reaches 10 MB
        retention="7 days", # Keep logs for 7 days
        compression="zip", # Compress rotated files
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,      # For asynchronous logging, good for performance
        backtrace=True,    # Better tracebacks in files
        diagnose=True      # Extended diagnosis for errors
    )

    logger.info("Logging configured.")
    logger.debug("This is a debug message, will only go to file by default.")

# setup_logging()
# logger.info("Application started.")
# try:
#     1 / 0
# except ZeroDivisionError:
#     logger.exception("A caught exception occurred!")

```

## Logging Practices

*   Log significant events: application start/stop, successful polls, new updates found, successful Reddit posts.
*   Log errors and warnings: network issues, API errors, parsing problems, configuration errors.
*   Include contextual information in logs where helpful (e.g., event ID when processing an event).
*   Avoid logging sensitive information (like API keys or passwords) unless absolutely necessary for debugging and ensure such logs are secured.

## Considerations

*   **Asynchronous Logging:** `enqueue=True` for file logging helps prevent logging from blocking the main application thread, which is important for a responsive polling application.
*   **Performance:** While `loguru` is efficient, avoid excessive logging in very high-frequency loops if it becomes a bottleneck. For this application, per-minute polling should not cause issues.
*   **Configuration:** Log levels and paths should be configurable, ideally through the main application configuration mechanism (`AppConfig` dataclass). 