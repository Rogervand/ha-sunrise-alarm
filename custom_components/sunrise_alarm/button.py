"""Snooze, dismiss and test buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SunriseAlarmConfigEntry
from .const import STATUS_IDLE, STATUS_RINGING
from .entity import SunriseAlarmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SunriseAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    m = entry.runtime_data
    async_add_entities(
        [SnoozeButton(m, "snooze"), DismissButton(m, "dismiss"), TestButton(m, "test")]
    )


class SnoozeButton(SunriseAlarmEntity, ButtonEntity):
    """Snooze a ringing alarm."""

    @property
    def available(self) -> bool:
        """Only usable while ringing."""
        return self.manager.status == STATUS_RINGING

    async def async_press(self) -> None:
        """Snooze."""
        await self.manager.async_snooze()


class DismissButton(SunriseAlarmEntity, ButtonEntity):
    """Stop the alarm (or skip a fade that has started)."""

    @property
    def available(self) -> bool:
        """Only usable while active."""
        return self.manager.status != STATUS_IDLE

    async def async_press(self) -> None:
        """Dismiss."""
        await self.manager.async_dismiss()


class TestButton(SunriseAlarmEntity, ButtonEntity):
    """Ring now to test the wake actions."""

    _attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        """Ring now."""
        self.manager.start_ringing()
