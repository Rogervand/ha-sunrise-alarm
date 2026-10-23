"""Behaviour tests for Sunrise Alarm Clock."""

from __future__ import annotations

from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.sunrise_alarm.const import DOMAIN

NEXT = "sensor.bedroom_next_alarm"
STATUS = "sensor.bedroom_status"


def local(y, mo, d, h, mi, s=0) -> datetime:
    return datetime(y, mo, d, h, mi, s, tzinfo=dt_util.get_default_time_zone())


async def advance(hass, freezer, delta: timedelta, step: float = 5) -> None:
    """Move time forward in small steps so sleeps and timers fire in order."""
    end = dt_util.utcnow() + delta
    while dt_util.utcnow() < end:
        freezer.tick(timedelta(seconds=min(step, (end - dt_util.utcnow()).total_seconds())))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()


@pytest.fixture
def calls(hass: HomeAssistant):
    hass.states.async_set(
        "light.bedside",
        "off",
        {"supported_color_modes": ["color_temp"], "min_color_temp_kelvin": 2700, "max_color_temp_kelvin": 6500},
    )
    hass.states.async_set("media_player.bedroom", "paused")
    return {
        "light_on": async_mock_service(hass, "light", "turn_on"),
        "volume": async_mock_service(hass, "media_player", "volume_set"),
        "play": async_mock_service(hass, "media_player", "play_media"),
        "source": async_mock_service(hass, "media_player", "select_source"),
        "pause": async_mock_service(hass, "media_player", "media_pause"),
    }


async def test_next_alarm_and_entities(hass, freezer: FrozenDateTimeFactory, calls, setup_alarm):
    # Setup ran at frozen "now"; pin a known time and recompute
    freezer.move_to(local(2026, 10, 22, 21, 0))  # Thursday evening
    await hass.services.async_call(
        "time", "set_value", {"entity_id": "time.bedroom_alarm_time", "time": "06:30"}, blocking=True
    )
    st = hass.states.get(NEXT)
    assert dt_util.parse_datetime(st.state) == local(2026, 10, 23, 6, 30)
    ents = st.attributes["entities"]
    assert ents["alarm_time"] == "time.bedroom_alarm_time"
    assert ents["days"]["sat"] == "switch.bedroom_saturday"
    assert ents["enabled"] == "switch.bedroom_alarm"

    # Friday off -> next is Monday
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.bedroom_friday"}, blocking=True)
    assert dt_util.parse_datetime(hass.states.get(NEXT).state) == local(2026, 10, 26, 6, 30)

    # Disable -> unknown
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.bedroom_alarm"}, blocking=True)
    assert hass.states.get(NEXT).state == "unknown"


async def test_full_wake_cycle(hass, freezer, calls, setup_alarm):
    freezer.move_to(local(2026, 10, 22, 6, 0))  # Thursday
    await hass.services.async_call(
        "time", "set_value", {"entity_id": "time.bedroom_alarm_time", "time": "06:30"}, blocking=True
    )
    assert hass.states.get(STATUS).state == "idle"

    events = []
    hass.bus.async_listen(f"{DOMAIN}_ringing", events.append)

    # Fade starts 10 min early (06:20)
    await advance(hass, freezer, timedelta(minutes=20, seconds=1))
    assert hass.states.get(STATUS).state == "pre_wake"
    first = calls["light_on"][0].data
    assert first["brightness_pct"] == 1
    assert first["color_temp_kelvin"] == 2700  # clamped to the bulb's minimum

    # Halfway through the fade brightness has climbed
    await advance(hass, freezer, timedelta(minutes=5))
    mid = calls["light_on"][-1].data["brightness_pct"]
    assert 40 <= mid <= 60

    # Ring at 06:30
    await advance(hass, freezer, timedelta(minutes=5))
    assert hass.states.get(STATUS).state == "ringing"
    assert len(events) == 1
    assert calls["volume"][0].data["volume_level"] == 0.05
    assert calls["play"][0].data["media_content_id"] == "FV:2/5"
    assert calls["light_on"][-1].data["brightness_pct"] == 100

    # Volume ramps to 25% over 2 minutes
    await advance(hass, freezer, timedelta(minutes=2, seconds=5))
    assert calls["volume"][-1].data["volume_level"] == 0.25

    # Snooze
    await hass.services.async_call("button", "press", {"entity_id": "button.bedroom_snooze"}, blocking=True)
    assert hass.states.get(STATUS).state == "snoozed"
    assert len(calls["pause"]) == 1
    assert hass.states.get("button.bedroom_snooze").state == "unavailable"
    snooze_until = dt_util.parse_datetime(hass.states.get(NEXT).state)
    assert abs((snooze_until - dt_util.now()) - timedelta(minutes=9)) < timedelta(seconds=2)

    # Rings again after 9 minutes
    await advance(hass, freezer, timedelta(minutes=9, seconds=5))
    assert hass.states.get(STATUS).state == "ringing"
    assert len(events) == 2

    # Dismiss -> idle, pause, next alarm is tomorrow (Friday)
    await hass.services.async_call(
        DOMAIN, "dismiss", {"config_entry_id": setup_alarm.entry_id}, blocking=True
    )
    assert hass.states.get(STATUS).state == "idle"
    assert len(calls["pause"]) == 2
    assert dt_util.parse_datetime(hass.states.get(NEXT).state) == local(2026, 10, 23, 6, 30)


async def test_auto_dismiss(hass, freezer, calls, setup_alarm):
    freezer.move_to(local(2026, 10, 22, 6, 0))
    await hass.services.async_call(DOMAIN, "trigger", {"config_entry_id": setup_alarm.entry_id}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "ringing"
    await advance(hass, freezer, timedelta(minutes=30, seconds=5), step=30)
    assert hass.states.get(STATUS).state == "idle"
    assert calls["pause"]


async def test_one_shot_disables_itself(hass, freezer, calls, setup_alarm):
    freezer.move_to(local(2026, 10, 22, 22, 0))
    await hass.services.async_call(
        DOMAIN, "set_days", {"config_entry_id": setup_alarm.entry_id, "days": []}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, "set_time", {"config_entry_id": setup_alarm.entry_id, "time": "22:05"}, blocking=True
    )
    assert dt_util.parse_datetime(hass.states.get(NEXT).state) == local(2026, 10, 22, 22, 5)
    await advance(hass, freezer, timedelta(minutes=5, seconds=2), step=10)
    assert hass.states.get(STATUS).state == "ringing"
    await hass.services.async_call("button", "press", {"entity_id": "button.bedroom_dismiss"}, blocking=True)
    assert hass.states.get("switch.bedroom_alarm").state == "off"
    assert hass.states.get(NEXT).state == "unknown"


async def test_dismiss_during_fade_skips_occurrence(hass, freezer, calls, setup_alarm):
    freezer.move_to(local(2026, 10, 22, 6, 0))
    await hass.services.async_call(
        DOMAIN, "set_time", {"config_entry_id": setup_alarm.entry_id, "time": "06:30"}, blocking=True
    )
    await advance(hass, freezer, timedelta(minutes=22), step=20)
    assert hass.states.get(STATUS).state == "pre_wake"
    await hass.services.async_call(DOMAIN, "dismiss", {"config_entry_id": setup_alarm.entry_id}, blocking=True)
    assert hass.states.get(STATUS).state == "idle"
    assert dt_util.parse_datetime(hass.states.get(NEXT).state) == local(2026, 10, 23, 6, 30)
    n = len(calls["play"])
    await advance(hass, freezer, timedelta(minutes=10), step=30)
    assert len(calls["play"]) == n  # did not ring
    assert hass.states.get("switch.bedroom_alarm").state == "on"


async def test_setting_alarm_inside_fade_window(hass, freezer, calls, setup_alarm):
    freezer.move_to(local(2026, 10, 22, 6, 25))
    await hass.services.async_call(
        DOMAIN, "set_time", {"config_entry_id": setup_alarm.entry_id, "time": "06:30"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "pre_wake"


async def test_state_persists_across_reload(hass, freezer, calls, setup_alarm):
    await hass.services.async_call(
        DOMAIN, "set_days", {"config_entry_id": setup_alarm.entry_id, "days": ["sat", "sun"]}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, "set_time", {"config_entry_id": setup_alarm.entry_id, "time": "08:15"}, blocking=True
    )
    freezer.tick(timedelta(seconds=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(setup_alarm.entry_id)
    await hass.async_block_till_done()
    st = hass.states.get(NEXT)
    assert st.attributes["days"] == ["sat", "sun"]
    assert st.attributes["alarm_time"] == "08:15"
    assert hass.states.get("switch.bedroom_monday").state == "off"


@pytest.mark.parametrize("options", [{"media_player": "media_player.bedroom", "source": "Morning Jazz", "volume_start": 10, "volume_end": 10, "volume_ramp_minutes": 0}])
async def test_source_and_no_lights(hass, freezer, calls, setup_alarm):
    await hass.services.async_call(DOMAIN, "trigger", {"config_entry_id": setup_alarm.entry_id}, blocking=True)
    await hass.async_block_till_done()
    assert calls["source"][0].data["source"] == "Morning Jazz"
    assert not calls["play"]
    assert not calls["light_on"]
    assert hass.states.get(NEXT).attributes["light_fade_minutes"] == 0


async def test_unload(hass, setup_alarm):
    assert await hass.config_entries.async_unload(setup_alarm.entry_id)
    await hass.async_block_till_done()


async def test_bad_entry_id(hass, setup_alarm):
    from homeassistant.exceptions import ServiceValidationError
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "snooze", {"config_entry_id": "nope"}, blocking=True)
