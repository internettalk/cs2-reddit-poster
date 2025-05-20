"""Client for interacting with the Reddit API using PRAW."""

import praw
import prawcore
from loguru import logger

from .data_models import AppConfig, ParsedSteamEvent


class RedditClient:
    """Handles authentication with Reddit and posting updates."""

    def __init__(self, config: AppConfig):
        self.config = config.reddit_credentials
        self.target_subreddit = config.reddit_subreddit
        self.reddit: praw.Reddit
        self._initialize_praw()

    def _initialize_praw(self) -> None:
        """Initializes the PRAW Reddit instance."""
        try:
            self.reddit = praw.Reddit(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                refresh_token=self.config.refresh_token,
                user_agent=self.config.user_agent,
            )
            # Check if authentication is working by fetching a basic piece of info
            # (e.g., bot's username or subreddit display name)
            # This will raise an exception if auth fails (e.g., bad refresh token)
            logger.info(f"PRAW initialized. Authenticated as user: {self.reddit.user.me()}")
            logger.info(f"Target subreddit: {self.target_subreddit}")
        except prawcore.exceptions.OAuthException as e:
            logger.critical(f"Reddit OAuthException during PRAW initialization: {e}. Check PRAW credentials, especially refresh_token.", exc_info=True)
            # Potentially raise a custom error or let the app handle it higher up
            raise  # Re-raise for now, main app should catch and exit gracefully
        except Exception as e:
            logger.critical(f"Failed to initialize PRAW Reddit instance: {e}", exc_info=True)
            raise

    def _format_post_title(self, event: ParsedSteamEvent) -> str:
        """Formats the title for the Reddit post."""
        # For now, use the event title directly. Can be customized later.
        return event.title

    def _format_post_body(self, event: ParsedSteamEvent) -> str:
        """Formats the body for the Reddit post (Markdown).

        Includes the event body (BBCode) and a link to the original announcement.
        """
        body_parts = []
        body_parts.append(event.body_bbcode)

        if event.url:
            body_parts.append(f"\n\n---\nSource: [{event.title}]({event.url})")
        else:
            body_parts.append(f"\n\n---\n(Source link not available)")
        
        # Add a small footer indicating it's a bot post
        body_parts.append("\n\n---\n^I'm ^a ^bot ^that ^posts ^CS2 ^game ^updates. ^Issues? ^Contact ^my ^developer.")

        return "\n".join(body_parts)

    def post_update(self, event: ParsedSteamEvent) -> bool:
        """Submits a new post to the configured subreddit for the given event.

        Returns True if successful, False otherwise.
        This method is async, but PRAW calls are synchronous, so they are run in a thread.
        """
        title = self._format_post_title(event)
        body = self._format_post_body(event)
        subreddit_name = self.target_subreddit

        logger.info(f"Attempting to post to r/{subreddit_name}: '{title}'")

        try:
            # PRAW's submit method is synchronous, run it in a thread
            # to avoid blocking the asyncio event loop.
            submission = self.reddit.subreddit(subreddit_name).submit(
                title=title,
                selftext=body
                # TODO: Add flair_id if specified in config and needed
            )
            logger.success(f"Successfully posted to r/{subreddit_name}: '{title}'. Post ID: {submission.id}, URL: {submission.shortlink}")
            return True
        except prawcore.exceptions.Forbidden as e:
            logger.error(f"Reddit API error (Forbidden 403): {e}. Check bot permissions on r/{subreddit_name}. Does the bot have posting rights? Is it banned?", exc_info=True)
        except prawcore.exceptions.PrawcoreException as e:
            logger.error(f"Reddit API error while posting to r/{subreddit_name}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred while posting to Reddit: {e}", exc_info=True)
        
        return False
