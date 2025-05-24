"""Client for interacting with the Reddit API using PRAW."""

import praw
import prawcore
from loguru import logger
from datetime import datetime, UTC
import bbcode
import html2text
from typing import Optional
import re

from .data_models import AppConfig, ParsedSteamEvent


class RedditClient:
    """Handles authentication with Reddit and posting updates."""

    def __init__(self, config: AppConfig):
        self.config = config.reddit_credentials
        self.target_subreddit = config.reddit_subreddit
        self.reddit_flair_text = config.reddit_flair_text
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
            logger.info(
                f"PRAW initialized. Authenticated as user: {self.reddit.user.me()}"
            )
            logger.info(f"Target subreddit: {self.target_subreddit}")
        except prawcore.exceptions.OAuthException as e:
            logger.critical(
                f"Reddit OAuthException during PRAW initialization: {e}. Check PRAW credentials, especially refresh_token.",
                exc_info=True,
            )
            # Potentially raise a custom error or let the app handle it higher up
            raise  # Re-raise for now, main app should catch and exit gracefully
        except Exception as e:
            logger.critical(
                f"Failed to initialize PRAW Reddit instance: {e}", exc_info=True
            )
            raise

    def _format_post_title(self, event: ParsedSteamEvent) -> str:
        """Formats the title for the Reddit post."""
        date_str = datetime.fromtimestamp(event.timestamp, UTC).strftime("%m/%d/%Y")
        base_title = f"Counter-Strike 2 Update for {date_str}"
        
        # Add sequence number suffix if this is not the first patch note of the day
        if event.sequence_number > 1:
            base_title += f" #{event.sequence_number}"
            
        return base_title

    def _convert_bbcode_to_markdown(self, bbcode_text: str) -> str:
        """Converts BBCode text to Markdown, then applies custom formatting for sections and subsections."""
        # First, convert BBCode to HTML
        parser = bbcode.Parser()
        html_output = parser.format(bbcode_text)

        # Then, convert HTML to Markdown
        h = html2text.HTML2Text()
        markdown_output = h.handle(html_output)
        markdown_output = (
            markdown_output.strip()
        )  # Remove any leading/trailing whitespace

        # Post-process for custom section/subsection formatting
        processed_lines = []
        section_pattern = re.compile(r"^\[\s*(.+?)\s*\]\s*$")
        subsection_pattern = re.compile(r"^([^\s\-*+][^:]*?):\s*$")
        for line in markdown_output.splitlines():
            # Section: [ SECTION_TITLE ] -> ## SECTION_TITLE
            section_match = section_pattern.match(line)
            if section_match:
                processed_lines.append(f"### {section_match.group(1).strip()}")
                continue
            # Subsection: SUBSECTION_TITLE: -> ### SUBSECTION_TITLE (not in bullet/indented)
            subsection_match = subsection_pattern.match(line)
            if subsection_match:
                processed_lines.append(f"#### {subsection_match.group(1).strip()}")
                continue
            processed_lines.append(line)
        return "\n".join(processed_lines)

    def _format_post_body(self, event: ParsedSteamEvent) -> str:
        """Formats the body for the Reddit post (Markdown).

        Includes the event body (BBCode) and a link to the original announcement.
        """
        body_parts = []
        # Convert BBCode to Markdown before appending
        markdown_body = self._convert_bbcode_to_markdown(event.body_bbcode)
        body_parts.append(markdown_body)

        return "\n".join(body_parts)

    def _find_flair_id(self, subreddit_name: str, flair_text: str) -> Optional[str]:
        """Finds the ID of a flair by its text on a subreddit."""
        if not flair_text:
            return None
        try:
            flairs = self.reddit.subreddit(subreddit_name).flair.link_templates
            for flair in flairs:
                if flair["text"] == flair_text:
                    logger.debug(
                        f"Found flair ID '{flair['id']}' for text '{flair_text}' on r/{subreddit_name}"
                    )
                    return flair["id"]
            logger.warning(
                f"Flair with text '{flair_text}' not found on r/{subreddit_name}. Available flairs: {[f['text'] for f in flairs]}"
            )
        except prawcore.exceptions.Forbidden:
            logger.warning(
                f"Bot does not have permission to access flairs on r/{subreddit_name}. Cannot apply flair."
            )
        except Exception as e:
            logger.error(
                f"Error finding flair ID for '{flair_text}' on r/{subreddit_name}: {e}",
                exc_info=True,
            )
        return None

    def _handle_submission_error(self, e: Exception, subreddit_name: str) -> None:
        """Handle common submission errors with appropriate logging."""
        if isinstance(e, prawcore.exceptions.Forbidden):
            logger.error(
                f"Reddit API error (Forbidden 403): {e}. Check bot permissions on r/{subreddit_name}. Does the bot have posting rights? Is it banned?",
                exc_info=True,
            )
        elif isinstance(e, prawcore.exceptions.PrawcoreException):
            logger.error(
                f"Reddit API error while posting to r/{subreddit_name}: {e}",
                exc_info=True,
            )
        else:
            logger.error(
                f"An unexpected error occurred while posting to Reddit: {e}",
                exc_info=True,
            )

    def post_update(self, event: ParsedSteamEvent) -> bool:
        """Submits a new post to the configured subreddit for the given event.

        For CS2 updates: Posts as self-post with formatted content
        For general announcements: Posts as link post with announcement title

        Returns True if successful, False otherwise.
        This method is async, but PRAW calls are synchronous, so they are run in a thread.
        """
        subreddit_name = self.target_subreddit
        flair_id_to_use = None

        if self.reddit_flair_text:
            logger.info(
                f"Attempting to find flair ID for '{self.reddit_flair_text}' on r/{subreddit_name}"
            )
            flair_id_to_use = self._find_flair_id(
                subreddit_name, self.reddit_flair_text
            )
            if flair_id_to_use:
                logger.info(
                    f"Using flair ID: {flair_id_to_use} for flair text: '{self.reddit_flair_text}'"
                )
            else:
                logger.warning(
                    f"Could not find flair ID for '{self.reddit_flair_text}'. Posting without flair."
                )

        # Prepare submission parameters based on event type
        if event.is_cs2_patchnote:
            title = self._format_post_title(event)
            submission_params = {
                "title": title,
                "url": event.url,
                "selftext": self._format_post_body(event),
                "send_replies": False,
            }
            post_type = "CS2 update"
        else:
            title = event.title
            submission_params = {
                "title": f"CS2 Blog Update: {title}",
                "url": event.url,
                "send_replies": False,
            }
            post_type = "general announcement"

        if flair_id_to_use:
            submission_params["flair_id"] = flair_id_to_use

        logger.info(f"Attempting to post {post_type} to r/{subreddit_name}: '{title}'")

        try:
            submission = self.reddit.subreddit(subreddit_name).submit(
                **submission_params
            )
            logger.success(
                f"Successfully posted {post_type} to r/{subreddit_name}: '{title}'. Post ID: {submission.id}, URL: {submission.shortlink}"
            )
            
            # For CS2 patch notes, also post the formatted body as a comment
            if event.is_cs2_patchnote:
                try:
                    formatted_body = self._format_post_body(event)
                    comment = submission.reply(formatted_body)
                    logger.success(
                        f"Successfully posted formatted body as comment. Comment ID: {comment.id}"
                    )
                except Exception as comment_error:
                    logger.error(
                        f"Failed to post formatted body as comment: {comment_error}",
                        exc_info=True,
                    )
                    # Don't return False here as the main post was successful
            
            return True
        except Exception as e:
            self._handle_submission_error(e, subreddit_name)
            return False
