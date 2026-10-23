"""Sunrise Alarm Clock for Home Assistant."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .card_loader import async_remove_card, async_setup_card
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DAYS,
    ATTR_ENABLED,
    ATTR_TIME,
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    DOMAIN,
    RAMP_MAX,
    RAMP_MIN,
    SERVICE_STOP,
    SERVICE_TRIGGER,
    SERVICE_UPDATE,
    SET_BRIGHTNESS,
    SET_FAVORITE_ID,
    SET_FAVORITE_NAME,
    SET_LIGHTS,
    SET_RAMP,
    SET_SPEAKER,
    SET_VOLUME_END,
    SET_VOLUME_START,
    STORAGE_VERSION,
    WEEKDAYS,
)
from .manager import AlarmManager

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

# Entity keys that exist in this version; anything else from 0.1.x is removed
ENTITY_KEYS = {"alarm_time", "enabled", "next_alarm", "status", "stop", "test"}

type SunriseAlarmConfigEntry = ConfigEntry[AlarmManager]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

ENTRY_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string})

_percent = vol.All(vol.Coerce(int), vol.Range(min=0, max=100))
_optional_str = vol.Any(None, cv.string)

UPDATE_SCHEMA = ENTRY_SCHEMA.extend(
    {
        vol.Optional(ATTR_TIME): cv.time,
        vol.Optional(ATTR_DAYS): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
        vol.Optional(ATTR_ENABLED): cv.boolean,
        vol.Optional(SET_SPEAKER): vol.Any(None, cv.entity_domain("media_player")),
        vol.Optional(SET_FAVORITE_ID): _optional_str,
        vol.Optional(SET_FAVORITE_NAME): _optional_str,
        vol.Optional(SET_VOLUME_START): _percent,
        vol.Optional(SET_VOLUME_END): _percent,
        vol.Optional(SET_LIGHTS): vol.All(cv.ensure_list, [cv.entity_domain("light")]),
        vol.Optional(SET_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=BRIGHTNESS_MIN, max=BRIGHTNESS_MAX)
        ),
        vol.Optional(SET_RAMP): vol.All(
            vol.Coerce(int), vol.Range(min=RAMP_MIN, max=RAMP_MAX)
        ),
    }
)
SETTING_KEYS = (
    SET_SPEAKER,
    SET_FAVORITE_ID,
    SET_FAVORITE_NAME,
    SET_VOLUME_START,
    SET_VOLUME_END,
    SET_LIGHTS,
    SET_BRIGHTNESS,
    SET_RAMP,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard card and register services."""
    await async_setup_card(hass)

    def _manager(call: ServiceCall) -> AlarmManager:
        entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_alarm",
                translation_placeholders={"entry_id": entry_id},
            )
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="alarm_not_loaded",
                translation_placeholders={"name": entry.title},
            )
        return entry.runtime_data

    async def update(call: ServiceCall) -> None:
        manager = _manager(call)
        settings: dict[str, Any] = {
            k: call.data[k] for k in SETTING_KEYS if k in call.data
        }
        merged = {**manager.settings, **settings}
        if int(merged[SET_VOLUME_END]) < int(merged[SET_VOLUME_START]):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="volume_order"
            )
        if SET_SPEAKER in settings and settings[SET_SPEAKER] is None:
            # No speaker means no music; forget the favorite too
            settings[SET_FAVORITE_ID] = settings[SET_FAVORITE_NAME] = None
        manager.update(
            alarm_time=call.data.get(ATTR_TIME),
            days=call.data.get(ATTR_DAYS),
            enabled=call.data.get(ATTR_ENABLED),
            settings=settings,
        )

    async def stop(call: ServiceCall) -> None:
        await _manager(call).async_stop()

    async def trigger(call: ServiceCall) -> None:
        _manager(call).start()

    hass.services.async_register(DOMAIN, SERVICE_UPDATE, update, UPDATE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP, stop, ENTRY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_TRIGGER, trigger, ENTRY_SCHEMA)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: SunriseAlarmConfigEntry
) -> bool:
    """Set up one alarm."""
    _remove_old_entities(hass, entry)
    manager = AlarmManager(hass, entry)
    await manager.async_load()
    entry.runtime_data = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # All entities exist now: refresh so the card can resolve their IDs
    manager.reschedule()
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SunriseAlarmConfigEntry
) -> bool:
    """Unload one alarm."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_unload()
    return unloaded


async def async_remove_entry(
    hass: HomeAssistant, entry: SunriseAlarmConfigEntry
) -> None:
    """Delete stored state when an alarm is removed."""
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
    remaining = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if not remaining:
        await async_remove_card(hass)


def _remove_old_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop entities from 0.1.x (day switches, snooze/dismiss) that no longer exist."""
    reg = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    for ent in er.async_entries_for_config_entry(reg, entry.entry_id):
        key = ent.unique_id.removeprefix(prefix)
        if key not in ENTITY_KEYS:
            reg.async_remove(ent.entity_id)
