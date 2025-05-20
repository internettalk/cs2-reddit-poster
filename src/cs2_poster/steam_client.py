import httpx
from loguru import logger
from typing import List, Optional, Dict, Any

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
            timeout=config.steam_poll_interval_seconds
        )
        self.base_url = "https://store.steampowered.com/events/ajaxgetpartnereventspageable/"
        self.params = {
            "clan_accountid": 0,
            "appid": 730,  # CS2 App ID
            "offset": 0,
            "count": 100, # Fetch up to 100 events
            "l": "english",
            "origin": "https://www.counter-strike.net",
        }
        logger.info("SteamClient initialized.")

    def _parse_event_data(self, event_data: Dict[str, Any]) -> Optional[ParsedSteamEvent]:
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
                logger.warning(f"Event data missing 'announcement_body'. Event GID: {event_data.get('gid')}")
                return None

            ann_gid = announcement.get("gid")
            title = announcement.get("headline")
            post_time = announcement.get("posttime") # This is RTime32 (Unix timestamp)
            body_content = announcement.get("body", "") # BBCode

            if not ann_gid or not title or post_time is None:
                logger.warning(f"Missing GID, title, or posttime in announcement data: {announcement}")
                return None

            # Filter out non-CS2 update events.
            normalized_title = title.lower()
            keywords = ["update", "release notes", "patch", "counter-strike 2"]
            if not any(keyword in normalized_title for keyword in keywords):
                logger.debug(f"Skipping event with title '{title}' as it doesn't seem to be a CS2 update (announcement GID: {ann_gid}).")
                return None
            
            event_url = f"https://store.steampowered.com/news/app/730/view/{ann_gid}"

            return ParsedSteamEvent(
                gid=ann_gid, # This is the announcement GID
                title=title,
                timestamp=post_time,
                body_bbcode=body_content,
                url=event_url
            )
        except Exception as e:
            logger.error(f"Error parsing event data: {e}. Data: {event_data}", exc_info=True)
            return None

    def fetch_latest_events(self, last_event_posttime: Optional[int] = None) -> List[ParsedSteamEvent]:
        """
        Fetches the latest CS2 events from Steam.

        Args:
            last_event_posttime: The Unix timestamp of the last processed event. 
                                 Events with a posttime newer than this will be returned.

        Returns:
            A list of ParsedSteamEvent objects, sorted from oldest to newest by posttime.
        """
        logger.info(f"Fetching latest events. Last processed posttime: {last_event_posttime}")
        newly_parsed_events: List[ParsedSteamEvent] = []
        try:
            response = self.http_client.get(self.base_url, params=self.params)
            response.raise_for_status()
            data = response.json()

            if not data.get("success") == 1:
                logger.error(f"Steam API indicated failure: {data.get('err_msg', 'No error message')}")
                return []

            raw_events = data.get("events", [])
            if not raw_events:
                logger.info("No events found in the Steam API response.")
                return []
            
            logger.debug(f"Received {len(raw_events)} raw events from Steam API.")

            # Events from the API are typically newest first.
            # We parse them and then sort by posttime before filtering.
            all_parsed_in_batch: List[ParsedSteamEvent] = []
            for event_data in raw_events:
                parsed_event = self._parse_event_data(event_data)
                if parsed_event:
                    all_parsed_in_batch.append(parsed_event)
            
            # Sort all successfully parsed events in this batch by their posttime, oldest to newest.
            all_parsed_in_batch.sort(key=lambda x: x.timestamp)

            # If there are events, select only the latest one.
            if all_parsed_in_batch:
                latest_event_in_batch = all_parsed_in_batch[-1] # Get the newest event
                # Now, we will only consider this single latest event for further processing.
                # The list 'all_parsed_in_batch' is effectively reduced to this one event for the logic below.
                all_parsed_in_batch = [latest_event_in_batch] 
            else:
                # If the batch was empty after parsing, there's nothing to select.
                all_parsed_in_batch = []

            if last_event_posttime is not None:
                # Filter out events that are not newer than last_event_posttime
                for pe in all_parsed_in_batch: # This loop will now run at most once
                    if pe.timestamp > last_event_posttime:
                        newly_parsed_events.append(pe)
                
                if newly_parsed_events:
                    logger.info(f"Found {len(newly_parsed_events)} events newer than posttime {last_event_posttime}.")
                else:
                    logger.info(f"No events found newer than posttime {last_event_posttime} in the current batch of {len(all_parsed_in_batch)} parsed events.")
            else:
                # If no last_event_posttime is provided (e.g., first run), all fetched (and parsed) events are new.
                logger.info("No last_event_posttime provided. Treating all fetched valid events as new.")
                newly_parsed_events = all_parsed_in_batch

            if newly_parsed_events:
                logger.info(f"Prepared {len(newly_parsed_events)} new events for processing, sorted oldest to newest by posttime.")
            else:
                logger.info("No new, valid CS2 update events found to process based on posttime.")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching Steam events: {e.response.status_code} - {e.response.text}", exc_info=True)
        except httpx.RequestError as e:
            logger.error(f"Network error fetching Steam events: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error fetching or parsing Steam events: {e}", exc_info=True)
        
        return newly_parsed_events # Already sorted oldest to newest

    def close(self):
        """
        Closes the httpx client.
        """
        logger.info("Closing SteamClient's HTTP client...")
        self.http_client.close()
        logger.info("SteamClient's HTTP client closed.") 