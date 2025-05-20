# Dataclasses Usage Specification

This document describes how Python's `dataclasses` will be utilized within the application for structuring data.

## Purpose

`dataclasses` will be used to create simple, yet robust, classes primarily for holding data. This is particularly useful for representing:

*   Parsed event data from the Steam API.
*   Configuration settings.
*   Data passed between different modules of the application.

## Benefits of Using Dataclasses

*   **Conciseness:** Reduces boilerplate code for `__init__`, `__repr__`, `__eq__`, etc.
*   **Type Hinting:** Encourages the use of type hints, improving code readability and allowing for static analysis.
*   **Readability:** Makes the structure of data clear and explicit.
*   **Immutability (Optional):** Can easily create immutable objects by setting `frozen=True`, which can be beneficial for data integrity in certain contexts.

## Example Structures

### Steam Event Data

When an event is fetched from the Steam API, relevant parts can be parsed into a dataclass.

```python
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass(frozen=True) # Consider frozen=True if events are not modified after creation
class SteamEvent:
    event_gid: str # Unique event identifier
    announcement_gid: str # Unique announcement identifier within the event
    clan_steamid: str
    event_name: str # Title of the event/update
    event_type: int # Numeric type of event
    appid: int
    rtime32_start_time: int # Unix timestamp for start
    rtime32_end_time: int
    comment_count: int
    creator_steamid: str
    last_update_steamid: str
    event_notes: str # Usually "patchnotes" for updates
    jsondata: dict = field(default_factory=dict) # For any extra JSON data like title, body_content
    # Potentially more fields based on actual API response structure
    # e.g., direct_link_url: Optional[str] = None

@dataclass(frozen=True)
class ParsedSteamEvent:
    gid: str # A unique ID for the announcement, could be event_gid or announcement_gid
    title: str
    body_bbcode: str # The raw BBCode content
    url: Optional[str] = None # Link to the announcement
    timestamp: int # rtime32_start_time or similar
```
*(Note: The exact fields for `SteamEvent` and `ParsedSteamEvent` will depend on the actual structure of the Steam API JSON response. This is a preliminary example.)*

### Application Configuration

```python
from dataclasses import dataclass

@dataclass
class RedditConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    user_agent: str
    username: str
    password: str # For the bot account
    subreddit: str

@dataclass
class AppConfig:
    steam_poll_interval_seconds: int = 60
    steam_api_url: str = "https://store.steampowered.com/events/ajaxgetpartnereventspageable/?clan_accountid=0&appid=730&offset=0&count=10&l=english&origin=https://www.counter-strike.net"
    log_file_path: str = "app.log"
    log_level_console: str = "INFO"
    log_level_file: str = "DEBUG"
    reddit: RedditConfig
    # state_file_path: str = "app_state.json" # For persisting last seen event ID
```

## Usage Guidelines

*   Use `dataclasses` for objects that are primarily data containers.
*   Leverage type hints for all fields.
*   Consider making dataclasses `frozen=True` if their instances should be immutable after creation, which is often a good practice for data flowing through the system.
*   For complex parsing or validation logic, dataclasses can still be used, but methods can be added to them, or parsing logic can be externalized to functions that return dataclass instances. 