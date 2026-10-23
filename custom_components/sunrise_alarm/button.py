"""Stop and test buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SunriseAlarmConfigEntry
from .const import STATUS_WAKING
from .entity import SunriseAlarmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SunriseAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    m = entry.runtime_data
    async_add_entities([StopButton(m, "stop"), TestButton(m, "test")])


class StopButton(SunriseAlarmEntity, ButtonEntity):
    """Stop a wake-up in progress."""

    @property
    def available(self) -> bool:
        """Only usable while waking."""
        return self.manager.status == STATUS_WAKING

    async def async_press(self) -> None:
        """Stop."""
        await self.manager.async_stop()


class TestButton(SunriseAlarmEntity, ButtonEntity):
    """Start the wake-up now."""

    _attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        """Start now."""
        self.manager.start()
