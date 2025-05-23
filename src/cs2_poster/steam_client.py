import httpx
from loguru import logger
from typing import Optional, Dict, Any

from .data_models import AppConfig, ParsedSteamEvent


class SteamClient:
    """
    Handles fetching and parsing CS2 game update events from Steam.
    """

    def __init__(self, config: AppConfig):
        """
        Initializes the SteamClient with application configuration.

        Args:
            config: The application configuration object.
        """
        self.config = config
        self.http_client = httpx.Client(
            headers={"User-Agent": "CS2UpdateAnnouncer/1.0"},
            timeout=config.steam_poll_interval_seconds,
        )
        self.base_url = (
            "https://store.steampowered.com/events/ajaxgetpartnereventspageable/"
        )
        self.params = {
            "clan_accountid": 0,
            "appid": 730,  # CS2 App ID
            "offset": 0,
            "count": 100,  # Fetch up to 100 events
            "l": "english",
            "origin": "https://www.counter-strike.net",
        }
        logger.info("SteamClient initialized.")

    def _parse_event_data(
        self, event_data: Dict[str, Any]
    ) -> Optional[ParsedSteamEvent]:
        """
        Parses raw event data from Steam into a ParsedSteamEvent object.

        Args:
            event_data: A dictionary representing a single event from Steam.

        Returns:
            A ParsedSteamEvent object if parsing is successful, None otherwise.
        """
        try:
            # The event_data itself contains the 'gid' for the event.
            # The announcement_body also has a 'gid', specific to the announcement.
            # We need the announcement details.
            announcement = event_data.get("announcement_body")
            if not announcement:
                logger.warning(
                    f"Event data missing 'announcement_body'. Event GID: {event_data.get('gid')}"
                )
                return None

            ann_gid = announcement.get("gid")
            title = announcement.get("headline")
            post_time = announcement.get("posttime")  # This is RTime32 (Unix timestamp)
            body_content = announcement.get("body", "")  # BBCode

            if not ann_gid or not title or post_time is None:
                logger.warning(
                    f"Missing GID, title, or posttime in announcement data: {announcement}"
                )
                return None

            # Process patch notes differently from other announcements.
            # The category, while visible on the page, isn't accessible via either JSON API or RSS feed.
            # So we need to check the title for keywords to determine if this is a patch note.
            # We don't want to post complex announcements as Markdown: we can't render it properly.
            normalized_title = title.lower()
            keywords = ["update", "release notes", "patch"]
            is_cs2_patchnote = any(keyword in normalized_title for keyword in keywords)

            if not is_cs2_patchnote:
                logger.debug(
                    f"Event with title '{title}' doesn't seem to be a CS2 update, but will post as general announcement (announcement GID: {ann_gid})."
                )

            event_url = f"https://store.steampowered.com/news/app/730/view/{ann_gid}"

            return ParsedSteamEvent(
                gid=ann_gid,  # This is the announcement GID
                title=title,
                timestamp=post_time,
                body_bbcode=body_content,
                url=event_url,
                is_cs2_patchnote=is_cs2_patchnote,
            )
        except Exception as e:
            logger.error(
                f"Error parsing event data: {e}. Data: {event_data}", exc_info=True
            )
            return None

    def fetch_latest_event(
        self, last_event_posttime: Optional[int] = None
    ) -> Optional[ParsedSteamEvent]:
        """
        Fetches the latest CS2 event from Steam.

        Args:
            last_event_posttime: The Unix timestamp of the last processed event.
                                 Only an event newer than this will be returned.

        Returns:
            The latest ParsedSteamEvent if it's new, otherwise None.
        """
        try:
            response = self.http_client.get(self.base_url, params=self.params)
            response.raise_for_status()
            data = response.json()

            if not data.get("success") == 1:
                logger.error(
                    f"Steam API indicated failure: {data.get('err_msg', 'No error message')}"
                )
                return None

            raw_events = data.get("events", [])
            if not raw_events:
                return None

            # Events from the API are typically newest first.
            for event_data in raw_events:
                parsed_event = self._parse_event_data(event_data)
                if parsed_event:
                    # Only consider the first valid event (newest)
                    if (
                        last_event_posttime is None
                        or parsed_event.timestamp > last_event_posttime
                    ):
                        return parsed_event
                    else:
                        return None
            return None
        except Exception as e:
            logger.error(f"Error fetching or parsing Steam event: {e}", exc_info=True)
            return None

    def close(self):
        """
        Closes the httpx client.
        """
        logger.info("Closing SteamClient's HTTP client...")
        self.http_client.close()
        logger.info("SteamClient's HTTP client closed.")
