"""Behaviour tests for Sunrise Alarm Clock."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
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


async def update(hass, entry, **data):
    await hass.services.async_call(
        DOMAIN, "update", {"config_entry_id": entry.entry_id, **data}, blocking=True
    )


@pytest.fixture
def calls(hass: HomeAssistant):
    hass.states.async_set("light.bedside", "off")
    hass.states.async_set("media_player.bedroom", "paused")
    return {
        "light_on": async_mock_service(hass, "light", "turn_on"),
        "volume": async_mock_service(hass, "media_player", "volume_set"),
        "play_media": async_mock_service(hass, "media_player", "play_media"),
        "play": async_mock_service(hass, "media_player", "media_play"),
        "pause": async_mock_service(hass, "media_player", "media_pause"),
    }


async def test_entities_and_schedule(hass, freezer, calls, setup_alarm):
    freezer.move_to(local(2026, 10, 22, 21, 0))  # Thursday evening
    await update(hass, setup_alarm, time="06:30")
    st = hass.states.get(NEXT)
    assert dt_util.parse_datetime(st.state) == local(2026, 10, 23, 6, 30)
    assert st.attributes["entities"] == {
        "alarm_time": "time.bedroom_alarm_time",
        "enabled": "switch.bedroom_alarm",
        "status": "sensor.bedroom_status",
        "stop": "button.bedroom_stop",
        "test": "button.bedroom_test_alarm",
    }
    assert st.attributes["settings"]["brightness"] == 80

    await update(hass, setup_alarm, days=["mon", "tue", "wed", "thu"])
    assert dt_util.parse_datetime(hass.states.get(NEXT).state) == local(2026, 10, 26, 6, 30)

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.bedroom_alarm"}, blocking=True
    )
    assert hass.states.get(NEXT).state == "unknown"

    # Only the six current entities exist
    reg = er.async_get(hass)
    assert len(er.async_entries_for_config_entry(reg, setup_alarm.entry_id)) == 6


async def test_wake_ramp_together(hass, freezer, calls, setup_alarm):
    freezer.move_to(local(2026, 10, 22, 6, 0))  # Thursday
    await update(
        hass,
        setup_alarm,
        time="06:30",
        speaker="media_player.bedroom",
        favorite_id="FV:2/5",
        favorite_name="Morning Jazz",
        volume_start=5,
        volume_end=25,
        lights=["light.bedside"],
        brightness=60,
        ramp_minutes=10,
    )
    events = []
    hass.bus.async_listen(f"{DOMAIN}_started", events.append)

    # Nothing happens before the alarm time
    await advance(hass, freezer, timedelta(minutes=29, seconds=55), step=30)
    assert not calls["light_on"] and not calls["play_media"]

    await advance(hass, freezer, timedelta(seconds=6))
    assert hass.states.get(STATUS).state == "waking"
    assert len(events) == 1
    assert calls["volume"][0].data["volume_level"] == 0.05
    pm = calls["play_media"][0].data
    assert pm["media_content_id"] == "FV:2/5"
    assert pm["media_content_type"] == "favorite_item_id"
    assert calls["light_on"][0].data["brightness_pct"] == 1
    assert "color_temp_kelvin" not in calls["light_on"][0].data

    # Halfway: both are about halfway
    await advance(hass, freezer, timedelta(minutes=5))
    assert 28 <= calls["light_on"][-1].data["brightness_pct"] <= 32
    assert 0.14 <= calls["volume"][-1].data["volume_level"] <= 0.16

    # End of ramp: lights at 60%, volume at 25%, back to idle, music keeps playing
    await advance(hass, freezer, timedelta(minutes=5, seconds=5))
    assert calls["light_on"][-1].data["brightness_pct"] == 60
    assert calls["volume"][-1].data["volume_level"] == 0.25
    assert hass.states.get(STATUS).state == "idle"
    assert not calls["pause"]
    assert dt_util.parse_datetime(hass.states.get(NEXT).state) == local(2026, 10, 23, 6, 30)


async def test_stop_pauses_music(hass, freezer, calls, setup_alarm):
    await update(
        hass, setup_alarm, speaker="media_player.bedroom", favorite_id="FV:2/5",
        lights=["light.bedside"], ramp_minutes=10,
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.bedroom_test_alarm"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("button.bedroom_stop").state != "unavailable"
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.bedroom_stop"}, blocking=True
    )
    assert hass.states.get(STATUS).state == "idle"
    assert len(calls["pause"]) == 1
    n = len(calls["light_on"])
    await advance(hass, freezer, timedelta(minutes=2), step=10)
    assert len(calls["light_on"]) == n  # ramp stopped


async def test_one_shot_switches_off(hass, freezer, calls, setup_alarm):
    freezer.move_to(local(2026, 10, 22, 22, 0))
    await update(hass, setup_alarm, days=[], time="22:05", lights=["light.bedside"], ramp_minutes=1)
    await advance(hass, freezer, timedelta(minutes=5, seconds=2), step=10)
    assert hass.states.get(STATUS).state == "waking"
    assert hass.states.get("switch.bedroom_alarm").state == "off"
    assert hass.states.get(NEXT).state == "unknown"


async def test_lights_only_and_speaker_without_favorite(hass, freezer, calls, setup_alarm):
    await update(hass, setup_alarm, lights=["light.bedside"], ramp_minutes=1, brightness=100)
    await hass.services.async_call(DOMAIN, "trigger", {"config_entry_id": setup_alarm.entry_id}, blocking=True)
    await advance(hass, freezer, timedelta(seconds=65), step=10)
    assert calls["light_on"][-1].data["brightness_pct"] == 100
    assert not calls["volume"]

    await update(hass, setup_alarm, speaker="media_player.bedroom", lights=[])
    await hass.services.async_call(DOMAIN, "trigger", {"config_entry_id": setup_alarm.entry_id}, blocking=True)
    await hass.async_block_till_done()
    assert calls["play"] and not calls["play_media"]


async def test_validation(hass, setup_alarm):
    with pytest.raises(ServiceValidationError):
        await update(hass, setup_alarm, volume_start=50, volume_end=10)
    with pytest.raises(Exception):  # brightness below 50%
        await update(hass, setup_alarm, brightness=30)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "stop", {"config_entry_id": "nope"}, blocking=True)
    # Clearing the speaker clears the favorite
    await update(hass, setup_alarm, speaker="media_player.x", favorite_id="FV:1", favorite_name="A")
    await update(hass, setup_alarm, speaker=None)
    s = hass.states.get(NEXT).attributes["settings"]
    assert s["speaker"] is None and s["favorite_id"] is None


async def test_persists_across_reload(hass, freezer, setup_alarm):
    await update(hass, setup_alarm, days=["sat", "sun"], time="08:15", brightness=90, favorite_id="FV:2/9")
    freezer.tick(timedelta(seconds=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(setup_alarm.entry_id)
    await hass.async_block_till_done()
    a = hass.states.get(NEXT).attributes
    assert a["days"] == ["sat", "sun"] and a["alarm_time"] == "08:15"
    assert a["settings"]["brightness"] == 90 and a["settings"]["favorite_id"] == "FV:2/9"


async def test_migrates_v01_alarm(hass, http_stub):
    """A 0.1.x alarm keeps its speaker/favorite/lights and loses old entities."""
    await hass.config.async_set_time_zone("America/Detroit")
    entry = MockConfigEntry(
        domain=DOMAIN, title="Bedroom", data={"name": "Bedroom"},
        options={"media_player": "media_player.bedroom", "media_content_type": "favorite_item_id",
                 "media_content_id": "FV:2/5", "lights": ["light.bedside"], "light_fade_minutes": 15,
                 "volume_start": 4, "volume_end": 20, "snooze_minutes": 9},
    )
    entry.add_to_hass(hass)
    reg = er.async_get(hass)
    reg.async_get_or_create("switch", DOMAIN, f"{entry.entry_id}_day_mon", config_entry=entry)
    reg.async_get_or_create("button", DOMAIN, f"{entry.entry_id}_snooze", config_entry=entry)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    s = hass.states.get(NEXT).attributes["settings"]
    assert s["speaker"] == "media_player.bedroom" and s["favorite_id"] == "FV:2/5"
    assert s["lights"] == ["light.bedside"] and s["ramp_minutes"] == 15 and s["volume_end"] == 20
    keys = {e.unique_id.split("_", 1)[1] for e in er.async_entries_for_config_entry(reg, entry.entry_id)}
    assert "day_mon" not in keys and "snooze" not in keys


async def test_unload(hass, setup_alarm):
    assert await hass.config_entries.async_unload(setup_alarm.entry_id)
