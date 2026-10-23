"""Sunrise Alarm Clock for Home Assistant."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DAYS,
    ATTR_TIME,
    CARD_URL,
    CARD_URL_BASE,
    DOMAIN,
    SERVICE_DISMISS,
    SERVICE_SET_DAYS,
    SERVICE_SET_TIME,
    SERVICE_SNOOZE,
    SERVICE_TRIGGER,
    VERSION,
    WEEKDAYS,
)
from .manager import AlarmManager

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

type SunriseAlarmConfigEntry = ConfigEntry[AlarmManager]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

ENTRY_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string})
SET_DAYS_SCHEMA = ENTRY_SCHEMA.extend(
    {vol.Required(ATTR_DAYS): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)])}
)
SET_TIME_SCHEMA = ENTRY_SCHEMA.extend({vol.Required(ATTR_TIME): cv.time})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard card and register services."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL_BASE, str(Path(__file__).parent / "frontend"), False
            )
        ]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")

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

    async def set_days(call: ServiceCall) -> None:
        _manager(call).set_days(call.data[ATTR_DAYS])

    async def set_time(call: ServiceCall) -> None:
        _manager(call).set_time(call.data[ATTR_TIME])

    async def snooze(call: ServiceCall) -> None:
        await _manager(call).async_snooze()

    async def dismiss(call: ServiceCall) -> None:
        await _manager(call).async_dismiss()

    async def trigger(call: ServiceCall) -> None:
        _manager(call).start_ringing()

    hass.services.async_register(DOMAIN, SERVICE_SET_DAYS, set_days, SET_DAYS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_TIME, set_time, SET_TIME_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SNOOZE, snooze, ENTRY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DISMISS, dismiss, ENTRY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_TRIGGER, trigger, ENTRY_SCHEMA)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: SunriseAlarmConfigEntry
) -> bool:
    """Set up one alarm."""
    manager = AlarmManager(hass, entry)
    await manager.async_load()
    entry.runtime_data = manager
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # All entities now exist: refresh so the card can resolve their IDs
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
    from homeassistant.helpers.storage import Store  # noqa: PLC0415

    from .const import STORAGE_VERSION  # noqa: PLC0415

    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()


async def _async_update_listener(
    hass: HomeAssistant, entry: SunriseAlarmConfigEntry
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
