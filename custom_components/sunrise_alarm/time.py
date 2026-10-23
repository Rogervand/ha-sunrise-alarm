"""Alarm time entity."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SunriseAlarmConfigEntry
from .entity import SunriseAlarmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SunriseAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the alarm time entity."""
    async_add_entities([AlarmTime(entry.runtime_data, "alarm_time")])


class AlarmTime(SunriseAlarmEntity, TimeEntity):
    """The time the wake-up starts."""

    @property
    def native_value(self) -> time:
        """Return the alarm time."""
        return self.manager.alarm_time

    async def async_set_value(self, value: time) -> None:
        """Change the alarm time."""
        self.manager.update(alarm_time=value)
