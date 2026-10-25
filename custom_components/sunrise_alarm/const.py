"""Constants for Sunrise Alarm Clock."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "sunrise_alarm"
VERSION: Final = "1.0.2"

STORAGE_VERSION: Final = 1

# Frontend card
CARD_FILENAME: Final = "sunrise-alarm-card.js"
CARD_URL_BASE: Final = f"/{DOMAIN}_static"
CARD_URL: Final = f"{CARD_URL_BASE}/{CARD_FILENAME}"

# Settings (all editable from the card)
SET_SPEAKER: Final = "speaker"
SET_FAVORITE_ID: Final = "favorite_id"
SET_FAVORITE_NAME: Final = "favorite_name"
SET_VOLUME_START: Final = "volume_start"
SET_VOLUME_END: Final = "volume_end"
SET_LIGHTS: Final = "lights"
SET_BRIGHTNESS: Final = "brightness"
SET_RAMP: Final = "ramp_minutes"

DEFAULT_SETTINGS: Final[dict[str, object]] = {
    SET_SPEAKER: None,
    SET_FAVORITE_ID: None,
    SET_FAVORITE_NAME: None,
    SET_VOLUME_START: 5,
    SET_VOLUME_END: 30,
    SET_LIGHTS: [],
    SET_BRIGHTNESS: 80,
    SET_RAMP: 10,
}

BRIGHTNESS_MIN: Final = 50
BRIGHTNESS_MAX: Final = 100
RAMP_MIN: Final = 1
RAMP_MAX: Final = 60

# Weekdays, Monday == 0 (matches datetime.weekday())
WEEKDAYS: Final = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Alarm status
STATUS_IDLE: Final = "idle"
STATUS_WAKING: Final = "waking"
STATUSES: Final = [STATUS_IDLE, STATUS_WAKING]

# Events fired on the bus
EVENT_STARTED: Final = f"{DOMAIN}_started"
EVENT_STOPPED: Final = f"{DOMAIN}_stopped"

# Services
SERVICE_UPDATE: Final = "update"
SERVICE_STOP: Final = "stop"
SERVICE_TRIGGER: Final = "trigger"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_TIME: Final = "time"
ATTR_DAYS: Final = "days"
ATTR_ENABLED: Final = "enabled"

# Ramp step interval (seconds)
STEP_SECONDS: Final = 10
