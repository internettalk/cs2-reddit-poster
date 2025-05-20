# PRAW OAuth Token Management Specification

This document outlines the strategy for securely storing and managing OAuth 2.0 credentials required by PRAW (Python Reddit API Wrapper) to interact with the Reddit API.

## 1. Credentials Involved

The primary credentials required for PRAW to operate on behalf of a Reddit user (bot account) are:

*   **`client_id`**: The client ID for your registered Reddit script application.
*   **`client_secret`**: The client secret for your registered Reddit script application.
*   **`refresh_token`**: A long-lived token used to obtain new access tokens without requiring repeated user authorization. This is crucial for unattended operation.
*   **`user_agent`**: A descriptive user agent string for your bot.
*   **`username`**: The Reddit username of the bot account (optional if PRAW is configured for script-type auth only, but often used with refresh token).
*   **`password`**: The Reddit password of the bot account (generally not stored directly if using refresh tokens for long-term auth, but might be needed for initial token acquisition).

The `refresh_token` is the most sensitive and critical piece for continuous operation.

## 2. Storage Strategies

Sensitive credentials **must not** be hardcoded into the application's source code. The following methods are recommended:

### 2.1. Environment Variables (Preferred Method)

*   **Description**: Store credentials as environment variables on the system where the application runs.
*   **Pros**:
    *   Keeps secrets out of the codebase.
    *   Widely supported by deployment platforms (Heroku, Docker, AWS, etc.).
    *   Considered a security best practice.
*   **Cons**:
    *   Requires setting up variables in each environment (development, staging, production).
*   **Implementation**:
    *   The application will read variables like `PRAW_CLIENT_ID`, `PRAW_CLIENT_SECRET`, `PRAW_REFRESH_TOKEN`, etc., at startup.
    *   The `python-dotenv` library will be used to load environment variables from a `.env` file during development. This `.env` file must be included in `.gitignore` to prevent accidental an unintended commit of secrets.

## 3. Loading Credentials into PRAW

PRAW can be configured with these credentials when initializing the `Reddit` instance:

```python
# Conceptual example
import praw
import os

# Assuming environment variables
reddit = praw.Reddit(
    client_id=os.environ.get("PRAW_CLIENT_ID"),
    client_secret=os.environ.get("PRAW_CLIENT_SECRET"),
    refresh_token=os.environ.get("PRAW_REFRESH_TOKEN"),
    user_agent=os.environ.get("PRAW_USER_AGENT"),
    # username=os.environ.get("PRAW_USERNAME"), # If needed by auth flow
)
```

This will likely be managed within the `AppConfig` dataclass structure.

## 4. Initial Refresh Token Acquisition

*   A `refresh_token` is typically obtained once through an OAuth authorization flow.
*   This often involves running a separate, one-time script that guides the user (developer) through logging into Reddit and authorizing the application. PRAW's documentation provides examples for this.
*   Once obtained, the `refresh_token` is stored using one of the secure methods above.

## 5. Security Best Practices

*   **Never hardcode credentials** in Python files or commit them to version control.
*   **Use `.gitignore`** diligently for any local credential files (e.g., `.env`, `secrets.ini`, `praw.ini`).
*   **Principle of Least Privilege**: The Reddit bot account should have only the necessary permissions on the target subreddit.
*   **Restrict File Permissions**: If using configuration files, ensure their file system permissions are as restrictive as possible.
*   **Regularly Review Access**: Periodically review your Reddit application settings and bot account access.

This strategy will be integrated into the application's configuration management, as detailed in `dataclasses-usage.md` (specifically the `AppConfig` and `RedditConfig` sections). 