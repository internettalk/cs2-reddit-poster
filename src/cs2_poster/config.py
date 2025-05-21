"""Configuration loading for the application."""

import os
from dotenv import load_dotenv
from .data_models import AppConfig, RedditCredentials


def load_configuration() -> AppConfig:
    """Loads application configuration from environment variables.

    Uses .env file for development environments.
    """
    load_dotenv()  # Load from .env file if present

    reddit_creds = RedditCredentials(
        client_id=os.environ["PRAW_CLIENT_ID"],
        client_secret=os.environ["PRAW_CLIENT_SECRET"],
        refresh_token=os.environ["PRAW_REFRESH_TOKEN"],
        user_agent=os.environ["PRAW_USER_AGENT"],
    )

    return AppConfig(
        steam_poll_interval_seconds=int(
            os.environ.get("STEAM_POLL_INTERVAL_SECONDS", 10)
        ),
        state_file_path=os.environ.get("STATE_FILE_PATH", "app_state.json"),
        reddit_credentials=reddit_creds,
        reddit_subreddit=os.environ["REDDIT_SUBREDDIT"],
        reddit_flair_text=os.environ.get("REDDIT_FLAIR_TEXT", "Game Update"),
    )
