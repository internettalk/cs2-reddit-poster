"""Main application entry point for the CS2 Update Announcer."""

import sys
import time
from typing import List
import praw  # Moved import praw to top
from urllib.parse import urlparse, parse_qs  # Added import

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


def polling_loop(
    config: AppConfig, steam_client: SteamClient, reddit_client: RedditClient
):
    """The main polling loop for fetching updates and posting them."""

    app_state = load_state(config)
    last_posttime = get_last_processed_posttime(app_state)
    last_reddit_post_time = get_last_reddit_post_time(app_state)
    logger.info(f"Initial last processed event posttime: {last_posttime}")
    logger.info(f"Initial last Reddit post time: {last_reddit_post_time}")

    while True:  # Changed from `while keep_running`
        logger.info("Polling for new CS2 updates...")
        try:
            new_events: List[ParsedSteamEvent] = steam_client.fetch_latest_events(
                last_event_posttime=last_posttime
            )

            if not new_events:
                logger.info("No new events to post.")
            else:
                logger.info(f"Found {len(new_events)} new event(s) to process.")
                processed_event_in_batch = False
                for event in new_events:  # Processed oldest to newest by steam_client
                    logger.info(
                        f"Processing event: GID '{event.gid}', Title '{event.title}'"
                    )

                    # Enforce 2-hour Reddit post rate limit
                    current_time = int(time.time())
                    if last_reddit_post_time is not None and (current_time - last_reddit_post_time) < 7200:
                        wait_time = 7200 - (current_time - last_reddit_post_time)
                        logger.warning(
                            f"Reddit post rate limit in effect. Last post was {current_time - last_reddit_post_time} seconds ago. Skipping posting. Next post allowed in {wait_time} seconds."
                        )
                        # Still update last_processed_event_posttime and save state
                        last_posttime = event.timestamp
                        set_last_processed_posttime(app_state, last_posttime)
                        save_state(app_state, config)
                        processed_event_in_batch = True
                        continue  # Move to next event in the batch

                    success = reddit_client.post_update(event)
                    if success:
                        last_posttime = event.timestamp  # Update last_posttime to the timestamp of the successfully posted event
                        set_last_processed_posttime(app_state, last_posttime)
                        last_reddit_post_time = current_time  # Update last_reddit_post_time
                        set_last_reddit_post_time(app_state, last_reddit_post_time)
                        save_state(
                            app_state, config
                        )  # Save state after each successful post
                        processed_event_in_batch = True
                        logger.info(
                            f"Successfully processed and posted event GID: {event.gid}, Posttime: {last_posttime}"
                        )
                    else:
                        logger.error(
                            f"Failed to post event GID: {event.gid}. Will retry this event in the next cycle if it's still fetched."
                        )
                        break  # Stop processing this batch on first error to avoid spamming or hitting rate limits

                if processed_event_in_batch:
                    logger.info("Finished processing batch of new events.")

        except Exception as e:
            logger.error(
                f"An unexpected error occurred in the polling loop: {e}", exc_info=True
            )
            # Continue loop after error, but wait before retrying to avoid rapid-fire errors
            # if it's a persistent issue.
            error_wait_time = 30  # seconds
            logger.info(
                f"Waiting for {error_wait_time} seconds after unexpected error before next poll."
            )
            time.sleep(error_wait_time)

        logger.debug(
            f"Waiting for {config.steam_poll_interval_seconds} seconds before next poll..."
        )
        time.sleep(config.steam_poll_interval_seconds)


@auth_app.command("refresh-token")
def generate_refresh_token(
    ctx: typer.Context,  # Access parent context if needed for config
    # Prompt for these, or consider making them options if preferred
):
    """
    Guides through the process of obtaining a new Reddit refresh token.
    You will need your app's Client ID, Client Secret, and a Redirect URI
    (set to http://localhost:8080 in your Reddit app settings).
    """
    logger.info("Starting refresh token generation process...")

    # Try to load existing config to get client_id, client_secret, user_agent
    # This assumes they are set in the environment or .env file
    # Alternatively, make these CLI options for this command.
    try:
        # Access the root command's context if necessary, or re-load
        # For simplicity here, we'll assume config is loaded or accessible
        # If main() is not run, app_config won't be globally available.
        # So, we should load config specifically for this command or pass via context.

        # For now, let's assume these are available or prompt the user.
        # For a more robust solution, these should be command options with prompts.
        app_config = load_configuration()  # Load config to get necessary details
        client_id = app_config.reddit_credentials.client_id
        client_secret = app_config.reddit_credentials.client_secret
        user_agent = app_config.reddit_credentials.user_agent

        if not all([client_id, client_secret, user_agent]):
            logger.error(
                "Client ID, Client Secret, or User Agent is missing in the configuration. These are required to generate a refresh token."
            )
            logger.info(
                "Please ensure PRAW_CLIENT_ID, PRAW_CLIENT_SECRET, and PRAW_USER_AGENT are set in your environment or .env file."
            )
            raise typer.Exit(code=1)

    except KeyError as e:
        missing_var = str(e).strip("'")
        logger.critical(
            f"FATAL: Missing required environment variable for refresh token generation: {missing_var}. Please set it and try again."
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"FATAL: Could not load configuration for refresh token generation: {e}"
        )
        sys.exit(1)

    redirect_uri = "http://localhost:8080"  # Standard redirect URI for PRAW script apps

    logger.info(f"Using Client ID: {client_id}")
    logger.info(f"Using User Agent: {user_agent}")
    logger.info(f"Using Redirect URI: {redirect_uri}")
    logger.warning("Ensure your Reddit app is configured with this exact Redirect URI.")

    # Initialize PRAW for authorization URL generation (no refresh token needed here)
    try:
        reddit_auth = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            user_agent=user_agent,
        )

        auth_url = reddit_auth.auth.url(
            scopes=["identity", "submit", "read", "flair"],
            state="cs2poster-auth",
            duration="permanent",
        )

        logger.info(
            "Please open the following URL in your browser to authorize the application:"
        )
        logger.info(auth_url)
        logger.info("Please copy the URL above and paste it into your browser.")

        logger.info(
            "After authorizing, you will be redirected to a URL that starts with 'http://localhost:8080'. Please paste the full redirected URL here."
        )
        full_redirect_url = typer.prompt("Enter the full redirected URL")

        if not full_redirect_url:
            logger.error("No redirect URL provided. Exiting.")
            raise typer.Exit(code=1)

        try:
            parsed_url = urlparse(full_redirect_url)
            query_params = parse_qs(parsed_url.query)
            auth_code_list = query_params.get("code")

            if not auth_code_list or not auth_code_list[0]:
                logger.error(
                    "Could not find 'code' parameter in the provided URL. Please ensure you pasted the correct and full redirect URL."
                )
                logger.debug(f"Parsed query params: {query_params}")
                raise typer.Exit(code=1)

            auth_code = auth_code_list[0]
            logger.debug(f"Extracted auth_code: {auth_code}")

        except Exception as e:
            logger.error(
                f"Failed to parse the redirect URL: {e}. Please ensure you pasted a valid URL.",
                exc_info=True,
            )
            raise typer.Exit(code=1)

        # The .strip() is still good practice in case of accidental whitespace during copy-paste
        # The previous auth_code.endswith("#_") check is no longer needed as parse_qs handles fragments correctly.
        logger.info("Attempting to fetch refresh token...")
        new_refresh_token = reddit_auth.auth.authorize(auth_code.strip())

        logger.success("Successfully obtained new refresh token!")
        print(f"\nYour new PRAW_REFRESH_TOKEN is: {new_refresh_token}\n")
        logger.info(
            "Please update your .env file or environment variable with this new token."
        )
        logger.info("For example, in your .env file, set:")
        logger.info(f"PRAW_REFRESH_TOKEN='{new_refresh_token}'")

    except Exception as e:
        logger.error(
            f"An error occurred during refresh token generation: {e}", exc_info=True
        )
        raise typer.Exit(code=1)


@app.command()
def main():
    """Entry point for the CS2 Update Announcer application."""
    setup_logging()
    try:
        app_config = load_configuration()
    except KeyError as e:
        missing_var = str(e).strip("'")
        logger.critical(
            f"FATAL: Missing required environment variable: {missing_var}. Please set it and try again.",
            exc_info=True,
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(f"FATAL: Could not load configuration: {e}", exc_info=True)
        sys.exit(1)

    logger.info("CS2 Update Announcer starting...")

    # Initialize clients
    # These might raise exceptions if critical setup (like Reddit auth) fails
    try:
        steam_client = SteamClient(app_config)
        reddit_client = RedditClient(app_config)  # Initializes PRAW and auth
    except Exception as e:
        logger.critical(
            f"Failed to initialize clients: {e}. Application cannot start.",
            exc_info=True,
        )
        sys.exit(1)

    if not reddit_client.reddit:  # Double check PRAW init success
        logger.critical(
            "Reddit client (PRAW) failed to initialize properly. Cannot start."
        )
        sys.exit(1)

    # Run the main polling loop
    try:
        polling_loop(app_config, steam_client, reddit_client)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down...")

    logger.info("CS2 Update Announcer shut down.")
    sys.exit(0)


if __name__ == "__main__":
    app()  # Use Typer to run the CLI application
