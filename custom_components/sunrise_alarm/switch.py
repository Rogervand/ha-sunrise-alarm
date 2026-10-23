"""Enable and weekday switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SunriseAlarmConfigEntry
from .const import WEEKDAYS
from .entity import SunriseAlarmEntity
from .manager import AlarmManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SunriseAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    manager = entry.runtime_data
    entities: list[SwitchEntity] = [AlarmEnabled(manager, "enabled")]
    entities += [AlarmDay(manager, i) for i in range(7)]
    async_add_entities(entities)


class AlarmEnabled(SunriseAlarmEntity, SwitchEntity):
    """Master on/off for the alarm."""

    @property
    def is_on(self) -> bool:
        """Return true if the alarm is armed."""
        return self.manager.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Arm."""
        self.manager.set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disarm."""
        self.manager.set_enabled(False)


class AlarmDay(SunriseAlarmEntity, SwitchEntity):
    """Whether the alarm repeats on a given weekday."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: AlarmManager, weekday: int) -> None:
        """Initialize."""
        super().__init__(manager, f"day_{WEEKDAYS[weekday]}")
        self._weekday = weekday

    @property
    def is_on(self) -> bool:
        """Return true if the alarm rings on this day."""
        return self._weekday in self.manager.days

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Add this day."""
        self.manager.set_day(self._weekday, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Remove this day."""
        self.manager.set_day(self._weekday, False)
