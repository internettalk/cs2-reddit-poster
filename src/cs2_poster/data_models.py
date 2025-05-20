"""Dataclasses for representing application data structures."""

from dataclasses import dataclass, field
from typing import List, Optional # Added Dict and Any based on spec


@dataclass(frozen=True)
class SteamApiResponse:
    """Represents the top-level structure of the Steam API response."""
    events: List['SteamEvent'] # Forward reference for SteamEvent


@dataclass(frozen=True)
class AnnouncementBody:
    """Represents the detailed announcement content within a Steam event."""
    gid: str
    clanid: str
    posterid: str
    headline: str
    posttime: int
    updatetime: int
    body: str  # This is the BBCode content
    commentcount: int
    tags: List[str]
    language: int
    hidden: int
    forum_topic_id: str
    event_gid: str
    voteupcount: int
    votedowncount: int
    ban_check_result: int
    banned: int


@dataclass(frozen=True)
class SteamEvent:
    """Represents a raw event structure from the Steam API.
    Updated based on sample JSON structure.
    """
    gid: str  # Unique event identifier (formerly event_gid)
    clan_steamid: str
    event_name: str  # Title of the event/update
    event_type: int  # Numeric type of event
    appid: int
    rtime32_start_time: int  # Unix timestamp for start
    rtime32_end_time: int
    comment_count: int
    creator_steamid: str
    last_update_steamid: str
    event_notes: str  # Often "see announcement body"
    jsondata: str # Raw JSON string, parse if needed.
    announcement_body: AnnouncementBody
    published: int
    hidden: int # Event hidden status
    rtime32_visibility_start: int
    rtime32_visibility_end: int
    broadcaster_accountid: int
    follower_count: int
    ignore_count: int
    forum_topic_id: str # Event's forum topic ID
    rtime32_last_modified: int
    news_post_gid: str # Can be "0"
    rtime_mod_reviewed: int
    featured_app_tagid: int
    unlisted: int
    votes_up: int
    votes_down: int
    comment_type: str
    gidfeature: str
    gidfeature2: str
    clan_steamid_original: str
    server_address: Optional[str] = None
    server_password: Optional[str] = None
    referenced_appids: List[int] = field(default_factory=list)
    build_id: Optional[int] = None
    build_branch: Optional[str] = None


@dataclass(frozen=True)
class ParsedSteamEvent:
    """Represents the essential information extracted from a Steam event's announcement body."""
    gid: str  # Unique ID for the announcement (from announcement_body.gid)
    title: str # From announcement_body.headline
    body_bbcode: str  # The raw BBCode content of the announcement (from announcement_body.body)
    timestamp: int  # Unix timestamp (from announcement_body.posttime)
    url: Optional[str] = None # Link to the announcement


@dataclass
class RedditCredentials:
    """Stores Reddit API credentials, loaded from environment variables."""
    client_id: str
    client_secret: str
    refresh_token: str
    user_agent: str
    username: Optional[str] = None # Optional, as per PRAW docs if refresh_token is primary
    password: Optional[str] = None # Optional, generally not stored/used with refresh_token


@dataclass
class AppConfig:
    """Main application configuration, loaded from environment variables."""
    reddit_credentials: RedditCredentials
    reddit_subreddit: str
    reddit_flair_text: Optional[str] = "Game Update" # Optional: Flair text to apply, e.g., "Game Update"
    steam_poll_interval_seconds: int = 60
    state_file_path: str = "app_state.json"
