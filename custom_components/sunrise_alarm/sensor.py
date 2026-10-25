"""Next-alarm and status sensors."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SunriseAlarmConfigEntry
from .const import DOMAIN, STATUSES
from .entity import SunriseAlarmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SunriseAlarmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    m = entry.runtime_data
    async_add_entities([NextAlarmSensor(m, "next_alarm"), StatusSensor(m, "status")])


class NextAlarmSensor(SunriseAlarmEntity, SensorEntity):
    """When the alarm next starts. Also carries everything the card shows."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _unrecorded_attributes = frozenset({"entities", "config_entry_id", "settings"})

    @property
    def native_value(self) -> datetime | None:
        """Return the next start time."""
        return self.manager.next_alarm

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose state and settings for the card."""
        m = self.manager
        return {
            "status": m.status,
            "alarm_time": m.alarm_time.strftime("%H:%M"),
            "enabled": m.enabled,
            "days": m.day_names,
            "off_at": m.off_at.isoformat() if m.off_at else None,
            "settings": dict(m.settings),
            "config_entry_id": m.entry.entry_id,
            "entities": self._related_entities(),
        }

    def _related_entities(self) -> dict[str, str | None]:
        reg = er.async_get(self.hass)
        prefix = self.manager.entry.entry_id

        def eid(platform: str, key: str) -> str | None:
            return reg.async_get_entity_id(platform, DOMAIN, f"{prefix}_{key}")

        return {
            "alarm_time": eid("time", "alarm_time"),
            "enabled": eid("switch", "enabled"),
            "status": eid("sensor", "status"),
            "stop": eid("button", "stop"),
            "test": eid("button", "test"),
        }


class StatusSensor(SunriseAlarmEntity, SensorEntity):
    """idle, waking (ramping up) or running (on until the run time ends)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUSES

    @property
    def native_value(self) -> str:
        """Return the status."""
        return self.manager.status
