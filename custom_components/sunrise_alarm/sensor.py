"""Next-alarm and status sensors."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SunriseAlarmConfigEntry
from .const import DOMAIN, STATUSES, WEEKDAYS
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
    """When the alarm will next ring. Also the card's anchor entity."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _unrecorded_attributes = frozenset({"entities", "config_entry_id"})

    @property
    def native_value(self) -> datetime | None:
        """Return the next ring time."""
        return self.manager.next_alarm

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose everything the card needs."""
        m = self.manager
        return {
            "status": m.status,
            "alarm_time": m.alarm_time.strftime("%H:%M"),
            "enabled": m.enabled,
            "days": m.day_names,
            "snooze_until": m.snooze_until.isoformat() if m.snooze_until else None,
            "light_fade_minutes": m.fade_minutes,
            "config_entry_id": m.entry.entry_id,
            "entities": self._related_entities(),
        }

    def _related_entities(self) -> dict[str, Any]:
        reg = er.async_get(self.hass)
        prefix = self.manager.entry.entry_id

        def eid(platform: str, key: str) -> str | None:
            return reg.async_get_entity_id(platform, DOMAIN, f"{prefix}_{key}")

        return {
            "alarm_time": eid("time", "alarm_time"),
            "enabled": eid("switch", "enabled"),
            "status": eid("sensor", "status"),
            "snooze": eid("button", "snooze"),
            "dismiss": eid("button", "dismiss"),
            "test": eid("button", "test"),
            "days": {d: eid("switch", f"day_{d}") for d in WEEKDAYS},
        }


class StatusSensor(SunriseAlarmEntity, SensorEntity):
    """idle / pre_wake / ringing / snoozed."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUSES

    @property
    def native_value(self) -> str:
        """Return the status."""
        return self.manager.status
