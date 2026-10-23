"""Constants for Sunrise Alarm Clock."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "sunrise_alarm"
VERSION: Final = "0.1.0"

STORAGE_VERSION: Final = 1

# Frontend card
CARD_FILENAME: Final = "sunrise-alarm-card.js"
CARD_URL_BASE: Final = f"/{DOMAIN}_static"
CARD_URL: Final = f"{CARD_URL_BASE}/{CARD_FILENAME}"

# Config / options keys
CONF_MEDIA_PLAYER: Final = "media_player"
CONF_MEDIA_CONTENT_ID: Final = "media_content_id"
CONF_MEDIA_CONTENT_TYPE: Final = "media_content_type"
CONF_SOURCE: Final = "source"
CONF_VOLUME_START: Final = "volume_start"
CONF_VOLUME_END: Final = "volume_end"
CONF_VOLUME_RAMP: Final = "volume_ramp_minutes"
CONF_LIGHTS: Final = "lights"
CONF_LIGHT_FADE: Final = "light_fade_minutes"
CONF_KELVIN_START: Final = "kelvin_start"
CONF_KELVIN_END: Final = "kelvin_end"
CONF_SNOOZE: Final = "snooze_minutes"
CONF_AUTO_DISMISS: Final = "auto_dismiss_minutes"

DEFAULTS: Final[dict[str, object]] = {
    CONF_MEDIA_CONTENT_TYPE: "music",
    CONF_VOLUME_START: 5,
    CONF_VOLUME_END: 30,
    CONF_VOLUME_RAMP: 5,
    CONF_LIGHTS: [],
    CONF_LIGHT_FADE: 15,
    CONF_KELVIN_START: 2200,
    CONF_KELVIN_END: 4000,
    CONF_SNOOZE: 9,
    CONF_AUTO_DISMISS: 30,
}

# Weekdays, Monday == 0 (matches datetime.weekday())
WEEKDAYS: Final = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Alarm status
STATUS_IDLE: Final = "idle"
STATUS_PRE_WAKE: Final = "pre_wake"
STATUS_RINGING: Final = "ringing"
STATUS_SNOOZED: Final = "snoozed"
STATUSES: Final = [STATUS_IDLE, STATUS_PRE_WAKE, STATUS_RINGING, STATUS_SNOOZED]

# Events fired on the bus
EVENT_PRE_WAKE: Final = f"{DOMAIN}_pre_wake"
EVENT_RINGING: Final = f"{DOMAIN}_ringing"
EVENT_SNOOZED: Final = f"{DOMAIN}_snoozed"
EVENT_DISMISSED: Final = f"{DOMAIN}_dismissed"

# Services
SERVICE_SET_DAYS: Final = "set_days"
SERVICE_SET_TIME: Final = "set_time"
SERVICE_SNOOZE: Final = "snooze"
SERVICE_DISMISS: Final = "dismiss"
SERVICE_TRIGGER: Final = "trigger"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_DAYS: Final = "days"
ATTR_TIME: Final = "time"

# Ramp step intervals (seconds)
VOLUME_STEP_SECONDS: Final = 10
LIGHT_STEP_SECONDS: Final = 20
