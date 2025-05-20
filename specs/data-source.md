# Data Source Specification

This document details the data source used by the application to fetch Counter-Strike update announcements.

## Source URL

The application will poll a JSON feed from the Steam platform.

*   **URL:** `https://store.steampowered.com/events/ajaxgetpartnereventspageable/?clan_accountid=0&appid=730&offset=0&count=100&l=english&origin=https://www.counter-strike.net`

## Parameters

*   `clan_accountid=0`: Specifies a global context, not tied to a specific Steam Community group.
*   `appid=730`: This is the application ID for Counter-Strike 2 (formerly Counter-Strike: Global Offensive).
*   `offset=0`: Starts fetching events from the most recent one.
*   `count=100`: Requests up to 100 events per call. This should be sufficient to catch new updates, assuming the polling interval is frequent enough.
*   `l=english`: Requests event data in English.
*   `origin=https://www.counter-strike.net`: Specifies the origin of the request, mimicking a request from the official Counter-Strike website.

## Data Format

The data is expected to be in JSON format. The specific structure of the event data will need to be investigated to identify relevant fields for update announcements (e.g., title, content, timestamp, URL).

## Considerations

*   **Rate Limiting:** The frequency of requests to this URL should be managed to avoid potential IP bans or rate limiting by Steam's servers. A polling interval of one minute is specified.
*   **Data Structure Changes:** The structure of the JSON response might change over time. The application should be designed to handle potential changes gracefully, perhaps with robust error handling and logging for unexpected data formats. 