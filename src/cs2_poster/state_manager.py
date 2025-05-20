"""Manages the persistent state of the application, like the last seen event ID."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from .data_models import AppConfig

STATE_KEY_LAST_EVENT_POSTTIME = "last_processed_event_posttime"


def load_state(config: AppConfig) -> Dict[str, Any]:
    """Loads the application state from the state file.

    Returns an empty dict if the file doesn't exist or is invalid.
    """
    state_file = Path(config.state_file_path)
    if state_file.exists() and state_file.is_file():
        try:
            with state_file.open("r", encoding="utf-8") as f:
                state_data = json.load(f)
                logger.info(f"Successfully loaded state from {state_file}")
                return state_data
        except json.JSONDecodeError as e:
            logger.warning(f"Could not decode JSON from state file {state_file}: {e}. Starting with empty state.")
        except IOError as e:
            logger.warning(f"Could not read state file {state_file}: {e}. Starting with empty state.")
    else:
        logger.info(f"State file {state_file} not found. Starting with empty state.")
    return {}


def save_state(state_data: Dict[str, Any], config: AppConfig) -> None:
    """Saves the application state to the state file."""
    state_file = Path(config.state_file_path)
    try:
        with state_file.open("w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)
        logger.debug(f"Successfully saved state to {state_file}")
    except IOError as e:
        logger.error(f"Could not write state file {state_file}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while saving state to {state_file}: {e}")


def get_last_processed_posttime(state: Dict[str, Any]) -> Optional[int]:
    """Retrieves the last processed event posttime from the state."""
    return state.get(STATE_KEY_LAST_EVENT_POSTTIME)


def set_last_processed_posttime(state: Dict[str, Any], posttime: int) -> None:
    """Updates the last processed event posttime in the state."""
    state[STATE_KEY_LAST_EVENT_POSTTIME] = posttime
    logger.info(f"Last processed event posttime set to: {posttime}") 