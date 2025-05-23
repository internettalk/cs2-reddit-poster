"""Main application entry point for the CS2 Update Announcer."""

import sys
import time
from typing import List, Optional, Tuple
import praw
from urllib.parse import urlparse, parse_qs

import typer
from loguru import logger

from .config import load_configuration
from .data_models import AppConfig, ParsedSteamEvent
from .logging_setup import setup_logging
from .reddit_client import RedditClient
from .state_manager import (
    get_last_processed_posttime,
    load_state,
    save_state,
    set_last_processed_posttime,
    get_last_reddit_post_time,
    set_last_reddit_post_time,
)
from .steam_client import SteamClient

app = typer.Typer(help="Monitors CS2 game updates and posts them to Reddit.")
# Create a new Typer app for the refresh token command to keep it separate
auth_app = typer.Typer(
    name="auth",
    help="Authentication utilities, e.g., for generating a new Reddit refresh token.",
)
app.add_typer(auth_app)


def initialize_polling_state(config: AppConfig) -> Tuple[object, Optional[int], Optional[int]]:
    """Initialize and return the polling state."""
    app_state = load_state(config)
    last_posttime = get_last_processed_posttime(app_state)
    last_reddit_post_time = get_last_reddit_post_time(app_state)
    
    logger.info(f"Initial last processed event posttime: {last_posttime}")
    logger.info(f"Initial last Reddit post time: {last_reddit_post_time}")
    
    return app_state, last_posttime, last_reddit_post_time


def should_skip_due_to_rate_limit(last_reddit_post_time: Optional[int]) -> bool:
    """Check if we should skip posting due to rate limiting."""
    if last_reddit_post_time is None:
        return False
    
    current_time = int(time.time())
    time_since_last_post = current_time - last_reddit_post_time
    
    if time_since_last_post < 7200:  # 2 hours
        wait_time = 7200 - time_since_last_post
        logger.warning(
            f"Reddit post rate limit in effect. Last post was {time_since_last_post} seconds ago. "
            f"Next post allowed in {wait_time} seconds."
        )
        return True
    
    return False


def process_event(
    event: ParsedSteamEvent,
    app_state: object,
    config: AppConfig,
    reddit_client: RedditClient,
    last_reddit_post_time: Optional[int]
) -> Tuple[int, Optional[int]]:
    """Process a single event and return updated timestamps."""
    logger.info(f"Processing event: GID '{event.gid}', Title '{event.title}'")
    
    # Check rate limit
    if should_skip_due_to_rate_limit(last_reddit_post_time):
        # Update state but skip posting
        set_last_processed_posttime(app_state, event.timestamp)
        save_state(app_state, config)
        return event.timestamp, last_reddit_post_time
    
    # Attempt to post
    success = reddit_client.post_update(event)
    if success:
        current_time = int(time.time())
        set_last_processed_posttime(app_state, event.timestamp)
        set_last_reddit_post_time(app_state, current_time)
        save_state(app_state, config)
        logger.info(f"Successfully processed and posted event GID: {event.gid}")
        return event.timestamp, current_time
    else:
        logger.error(f"Failed to post event GID: {event.gid}. Will retry in next cycle.")
        return event.timestamp, last_reddit_post_time


def polling_loop(config: AppConfig, steam_client: SteamClient, reddit_client: RedditClient):
    """The main polling loop for fetching updates and posting them."""
    app_state, last_posttime, last_reddit_post_time = initialize_polling_state(config)

    while True:
        logger.info("Polling for new CS2 updates...")
        try:
            event = steam_client.fetch_latest_event(last_event_posttime=last_posttime)

            if not event:
                logger.info("No new event to post.")
            else:
                last_posttime, last_reddit_post_time = process_event(
                    event, app_state, config, reddit_client, last_reddit_post_time
                )

        except Exception as e:
            logger.error(f"Unexpected error in polling loop: {e}", exc_info=True)
            time.sleep(30)  # Wait 30 seconds after error
            continue

        logger.debug(f"Waiting {config.steam_poll_interval_seconds} seconds before next poll...")
        time.sleep(config.steam_poll_interval_seconds)


def setup_praw(app_config: AppConfig) -> praw.Reddit:
    """Setup Reddit authentication for token generation."""
    creds = app_config.reddit_credentials
    if not all([creds.client_id, creds.client_secret, creds.user_agent]):
        raise ValueError("Missing Reddit credentials (client_id, client_secret, or user_agent)")
    
    return praw.Reddit(
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        redirect_uri="http://localhost:8080",
        user_agent=creds.user_agent,
    )


def get_auth_code_from_user(reddit_auth: praw.Reddit) -> str:
    """Get authorization code from user interaction."""
    auth_url = reddit_auth.auth.url(
        scopes=["identity", "submit", "read", "flair"],
        state="cs2poster-auth",
        duration="permanent",
    )

    logger.info("Please open this URL in your browser:")
    logger.info(auth_url)
    
    redirect_url = typer.prompt(
        "After authorizing, paste the full redirect URL (starting with http://localhost:8080)"
    )
    
    if not redirect_url:
        raise ValueError("No redirect URL provided")

    # Extract auth code from redirect URL
    parsed_url = urlparse(redirect_url)
    query_params = parse_qs(parsed_url.query)
    auth_code_list = query_params.get("code")

    if not auth_code_list or not auth_code_list[0]:
        raise ValueError("Could not find 'code' parameter in the redirect URL")

    return auth_code_list[0].strip()


@auth_app.command("refresh-token")
def generate_refresh_token():
    """Generate a new Reddit refresh token."""
    logger.info("Starting refresh token generation...")

    try:
        app_config = load_configuration()
        praw_instance = setup_praw(app_config)
        auth_code = get_auth_code_from_user(praw_instance)
        
        logger.info("Fetching refresh token...")
        refresh_token = praw_instance.auth.authorize(auth_code)

        logger.success("Successfully obtained new refresh token!")
        print(f"\nYour new PRAW_REFRESH_TOKEN: {refresh_token}\n")
        logger.info("Add this to your .env file:")
        logger.info(f"PRAW_REFRESH_TOKEN='{refresh_token}'")

    except Exception as e:
        logger.error(f"Error generating refresh token: {e}", exc_info=True)
        raise typer.Exit(code=1)


def initialize_clients(app_config: AppConfig) -> Tuple[SteamClient, RedditClient]:
    """Initialize and return Steam and Reddit clients."""
    try:
        steam_client = SteamClient(app_config)
        reddit_client = RedditClient(app_config)
        
        if not reddit_client.reddit:
            raise RuntimeError("Reddit client failed to initialize")
            
        return steam_client, reddit_client
        
    except Exception as e:
        logger.critical(f"Failed to initialize clients: {e}", exc_info=True)
        sys.exit(1)


@app.command()
def main():
    """Entry point for the CS2 Update Announcer application."""
    setup_logging()
    
    try:
        app_config = load_configuration()
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}", exc_info=True)
        sys.exit(1)

    logger.info("CS2 Update Announcer starting...")
    
    steam_client, reddit_client = initialize_clients(app_config)
    
    try:
        polling_loop(app_config, steam_client, reddit_client)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down...")

    logger.info("CS2 Update Announcer shut down.")


if __name__ == "__main__":
    app()  # Use Typer to run the CLI application
