# Reddit Integration Specification

This document outlines how the application will interact with Reddit to post update announcements.

## Objective

To automatically create new submissions on a designated subreddit when a new Counter-Strike update is detected.

## Authentication

*   The application will need to authenticate with the Reddit API.
*   This typically involves registering a script-type application on Reddit to obtain a client ID and client secret.
*   A refresh token will also be required for unattended, long-term operation.
*   Credentials (client ID, client secret, refresh token, username, password of the bot account) must be securely managed and not hardcoded into the source code. Environment variables or a configuration file (added to `.gitignore`) are recommended.

## Reddit API Library

*   The Python Reddit API Wrapper (PRAW) will be used for all interactions with the Reddit API. It provides a convenient way to authenticate, fetch data, and submit content.

## Posting Logic

1.  **Subreddit:** The target subreddit for posting announcements needs to be configurable.
2.  **Post Title:** The title of the Reddit post should be clear and informative, likely derived from the update's title or key information.
3.  **Post Body:**
    *   The body of the post should contain the main content of the update announcement.
    *   It should be formatted for readability on Reddit (Markdown).
    *   A direct link to the official Steam announcement should be included if available.
4.  **Flair (Optional):** If the target subreddit uses flairs, the application could be configured to assign a specific flair to update posts (e.g., "Update").
5.  **Duplicate Prevention:** While the polling mechanism aims to fetch only new updates, an additional check before posting to Reddit (e.g., searching for a similar post title or link recently) could be a failsafe, though this adds complexity and might not be necessary if the primary update identification logic is robust.

## Error Handling

*   **API Errors:** Handle potential errors from the Reddit API (e.g., rate limits, authentication failures, invalid subreddit, posting errors).
*   **Formatting Errors:** Ensure the content is correctly formatted before attempting to post.
*   Logging of successful posts and any errors encountered during the posting process is essential.

## Configuration

The following should be configurable:
*   Reddit API credentials (as mentioned in Authentication).
*   Target subreddit name.
*   Post title format (if customization beyond the direct update title is needed).
*   Optional: Post flair ID. 