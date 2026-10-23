"""Alarm on/off switch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SunriseAlarmConfigEntry
from .entity import SunriseAlarmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SunriseAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch."""
    async_add_entities([AlarmEnabled(entry.runtime_data, "enabled")])


class AlarmEnabled(SunriseAlarmEntity, SwitchEntity):
    """Arms or disarms the alarm."""

    @property
    def is_on(self) -> bool:
        """Return true if the alarm is armed."""
        return self.manager.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Arm."""
        self.manager.update(enabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disarm."""
        self.manager.update(enabled=False)
