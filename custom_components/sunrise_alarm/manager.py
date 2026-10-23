"""Alarm state, scheduling and wake sequences."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AUTO_DISMISS,
    CONF_KELVIN_END,
    CONF_KELVIN_START,
    CONF_LIGHT_FADE,
    CONF_LIGHTS,
    CONF_MEDIA_CONTENT_ID,
    CONF_MEDIA_CONTENT_TYPE,
    CONF_MEDIA_PLAYER,
    CONF_SNOOZE,
    CONF_SOURCE,
    CONF_VOLUME_END,
    CONF_VOLUME_RAMP,
    CONF_VOLUME_START,
    DEFAULTS,
    DOMAIN,
    EVENT_DISMISSED,
    EVENT_PRE_WAKE,
    EVENT_RINGING,
    EVENT_SNOOZED,
    LIGHT_STEP_SECONDS,
    STATUS_IDLE,
    STATUS_PRE_WAKE,
    STATUS_RINGING,
    STATUS_SNOOZED,
    STORAGE_VERSION,
    VOLUME_STEP_SECONDS,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIME = time(7, 0)
DEFAULT_DAYS = [0, 1, 2, 3, 4]


class AlarmManager:
    """Owns one alarm: its persisted state, timers and wake actions."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )

        # Persisted state
        self.alarm_time: time = DEFAULT_TIME
        self.days: set[int] = set(DEFAULT_DAYS)
        self.enabled: bool = True

        # Runtime state
        self.status: str = STATUS_IDLE
        self.next_alarm: datetime | None = None
        self.snooze_until: datetime | None = None
        self.last_rang: datetime | None = None
        self._skipped: datetime | None = None

        self._listeners: list[Callable[[], None]] = []
        self._timers: list[CALLBACK_TYPE] = []
        self._auto_dismiss: CALLBACK_TYPE | None = None
        self._light_task: asyncio.Task | None = None
        self._volume_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def opt(self, key: str) -> Any:
        """Return a setting from options, falling back to data and defaults."""
        if key in self.entry.options:
            return self.entry.options[key]
        if key in self.entry.data:
            return self.entry.data[key]
        return DEFAULTS.get(key)

    @property
    def lights(self) -> list[str]:
        """Configured lights."""
        return list(self.opt(CONF_LIGHTS) or [])

    @property
    def media_player(self) -> str | None:
        """Configured media player."""
        return self.opt(CONF_MEDIA_PLAYER) or None

    @property
    def fade_minutes(self) -> float:
        """Light fade-in length; zero when no lights are configured."""
        return float(self.opt(CONF_LIGHT_FADE) or 0) if self.lights else 0.0

    @property
    def is_repeating(self) -> bool:
        """True when at least one weekday is selected."""
        return bool(self.days)

    @property
    def day_names(self) -> list[str]:
        """Selected weekdays as short names, Monday first."""
        return [WEEKDAYS[d] for d in sorted(self.days)]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_load(self) -> None:
        """Load persisted state and schedule the next alarm."""
        if (stored := await self._store.async_load()) is not None:
            try:
                self.alarm_time = time.fromisoformat(stored["time"])
            except (KeyError, ValueError):
                self.alarm_time = DEFAULT_TIME
            self.days = {
                WEEKDAYS.index(d) for d in stored.get("days", []) if d in WEEKDAYS
            }
            self.enabled = bool(stored.get("enabled", True))
        self.reschedule()

    async def async_unload(self) -> None:
        """Cancel everything; called when the entry unloads."""
        self._cancel_timers()
        self._cancel_auto_dismiss()
        await self._cancel_tasks()

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(
            lambda: {
                "time": self.alarm_time.strftime("%H:%M"),
                "days": self.day_names,
                "enabled": self.enabled,
            },
            1,
        )

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        """Register an entity update callback."""
        self._listeners.append(update)

        @callback
        def remove() -> None:
            self._listeners.remove(update)

        return remove

    @callback
    def _notify(self) -> None:
        for update in list(self._listeners):
            update()

    # ------------------------------------------------------------------
    # Mutators (called by entities and services)
    # ------------------------------------------------------------------
    @callback
    def set_time(self, value: time) -> None:
        """Set the alarm time."""
        self.alarm_time = value.replace(second=0, microsecond=0)
        self._save()
        self.reschedule()

    @callback
    def set_days(self, days: list[str]) -> None:
        """Replace the set of weekdays."""
        self.days = {WEEKDAYS.index(d) for d in days if d in WEEKDAYS}
        self._save()
        self.reschedule()

    @callback
    def set_day(self, weekday: int, on: bool) -> None:
        """Toggle a single weekday."""
        if on:
            self.days.add(weekday)
        else:
            self.days.discard(weekday)
        self._save()
        self.reschedule()

    @callback
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the alarm."""
        self.enabled = enabled
        self._save()
        self.reschedule()

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    def compute_next(self, now: datetime) -> datetime | None:
        """Return the next ring time strictly after ``now``, or None."""
        if not self.enabled:
            return None
        tz = dt_util.get_default_time_zone()
        local_now = now.astimezone(tz)
        today: date = local_now.date()
        for offset in range(8):
            day = today + timedelta(days=offset)
            if self.days and day.weekday() not in self.days:
                continue
            candidate = datetime.combine(day, self.alarm_time, tzinfo=tz)
            # Normalise so nonexistent DST times resolve to a real instant
            candidate = dt_util.as_local(dt_util.as_utc(candidate))
            if candidate > local_now and candidate != self._skipped:
                return candidate
        return None

    @callback
    def reschedule(self) -> None:
        """Recompute the next alarm and (re)arm timers."""
        self._cancel_timers()
        now = dt_util.now()

        if self.status == STATUS_SNOOZED and self.snooze_until:
            self.next_alarm = self.snooze_until
            self._timers.append(
                async_track_point_in_time(
                    self.hass, self._handle_ring, self.snooze_until
                )
            )
            self._notify()
            return

        if self.status in (STATUS_RINGING,):
            # Don't arm the next occurrence until this one is dismissed
            self._notify()
            return

        self.next_alarm = self.compute_next(now)
        if self.next_alarm is None:
            if self.status == STATUS_PRE_WAKE:
                self._abort_pre_wake()
            self._notify()
            return

        fade = self.fade_minutes
        if fade > 0:
            pre_wake = self.next_alarm - timedelta(minutes=fade)
            if pre_wake > now:
                if self.status == STATUS_PRE_WAKE:
                    # Alarm moved later; restart the fade at the right time
                    self._abort_pre_wake()
                self._timers.append(
                    async_track_point_in_time(
                        self.hass, self._handle_pre_wake, pre_wake
                    )
                )
            elif self.status != STATUS_PRE_WAKE:
                # Inside the fade window already: start now with what's left
                self._start_pre_wake((self.next_alarm - now).total_seconds())
        elif self.status == STATUS_PRE_WAKE:
            self._abort_pre_wake()

        self._timers.append(
            async_track_point_in_time(self.hass, self._handle_ring, self.next_alarm)
        )
        self._notify()

    @callback
    def _cancel_timers(self) -> None:
        while self._timers:
            self._timers.pop()()

    @callback
    def _cancel_auto_dismiss(self) -> None:
        if self._auto_dismiss:
            self._auto_dismiss()
            self._auto_dismiss = None

    async def _cancel_tasks(self) -> None:
        for task in (self._light_task, self._volume_task):
            if task and not task.done():
                task.cancel()
        self._light_task = self._volume_task = None

    @callback
    def _cancel_task(self, attr: str) -> None:
        task: asyncio.Task | None = getattr(self, attr)
        if task and not task.done():
            task.cancel()
        setattr(self, attr, None)

    def _event_data(self) -> dict[str, Any]:
        return {
            "config_entry_id": self.entry.entry_id,
            "name": self.entry.title,
            "alarm_time": self.alarm_time.strftime("%H:%M"),
        }

    # ------------------------------------------------------------------
    # Pre-wake (light fade)
    # ------------------------------------------------------------------
    @callback
    def _handle_pre_wake(self, _now: datetime) -> None:
        self._start_pre_wake(self.fade_minutes * 60)

    @callback
    def _start_pre_wake(self, seconds: float) -> None:
        self.status = STATUS_PRE_WAKE
        self.hass.bus.async_fire(EVENT_PRE_WAKE, self._event_data())
        self._cancel_task("_light_task")
        self._light_task = self.entry.async_create_background_task(
            self.hass, self._fade_lights(seconds), f"{DOMAIN} light fade"
        )
        self._notify()

    @callback
    def _abort_pre_wake(self) -> None:
        self._cancel_task("_light_task")
        self.status = STATUS_IDLE

    async def _fade_lights(self, seconds: float) -> None:
        """Step brightness 1% -> 100% (and warm -> cool) over ``seconds``."""
        lights = self.lights
        if not lights:
            return
        k_start = int(self.opt(CONF_KELVIN_START))
        k_end = int(self.opt(CONF_KELVIN_END))
        steps = max(1, int(seconds // LIGHT_STEP_SECONDS))
        step_len = seconds / steps
        for i in range(steps + 1):
            frac = i / steps
            brightness = max(1, round(1 + 99 * frac))
            kelvin = round(k_start + (k_end - k_start) * frac)
            await self._lights_on(lights, brightness, kelvin, step_len if i else 1)
            if i < steps:
                await asyncio.sleep(step_len)

    async def _lights_on(
        self, lights: list[str], brightness: int, kelvin: int | None, transition: float
    ) -> None:
        for light in lights:
            data: dict[str, Any] = {
                ATTR_ENTITY_ID: light,
                "brightness_pct": brightness,
                "transition": round(transition, 1),
            }
            if kelvin is not None and (state := self.hass.states.get(light)):
                modes = state.attributes.get("supported_color_modes") or []
                if "color_temp" in modes:
                    lo = state.attributes.get("min_color_temp_kelvin") or kelvin
                    hi = state.attributes.get("max_color_temp_kelvin") or kelvin
                    data["color_temp_kelvin"] = min(max(kelvin, lo), hi)
            await self._call("light", "turn_on", data)

    # ------------------------------------------------------------------
    # Ringing
    # ------------------------------------------------------------------
    @callback
    def _handle_ring(self, _now: datetime) -> None:
        self.start_ringing()

    @callback
    def start_ringing(self) -> None:
        """Start the alarm now (also used by the test service)."""
        self._cancel_timers()
        self._cancel_task("_light_task")
        self._cancel_task("_volume_task")
        self.status = STATUS_RINGING
        self.snooze_until = None
        self.next_alarm = None
        self.last_rang = dt_util.now()
        self.hass.bus.async_fire(EVENT_RINGING, self._event_data())

        if self.lights:
            self.entry.async_create_background_task(
                self.hass,
                self._lights_on(self.lights, 100, int(self.opt(CONF_KELVIN_END)), 3),
                f"{DOMAIN} lights full",
            )
        if self.media_player:
            self._volume_task = self.entry.async_create_background_task(
                self.hass, self._play_and_ramp(), f"{DOMAIN} volume ramp"
            )

        self._cancel_auto_dismiss()
        if (minutes := self.opt(CONF_AUTO_DISMISS)) and float(minutes) > 0:
            self._auto_dismiss = async_track_point_in_time(
                self.hass,
                self._handle_auto_dismiss,
                dt_util.now() + timedelta(minutes=float(minutes)),
            )
        self._notify()

    async def _play_and_ramp(self) -> None:
        player = self.media_player
        assert player
        v_start = float(self.opt(CONF_VOLUME_START)) / 100
        v_end = float(self.opt(CONF_VOLUME_END)) / 100
        ramp = float(self.opt(CONF_VOLUME_RAMP) or 0) * 60

        await self._call(
            "media_player",
            "volume_set",
            {ATTR_ENTITY_ID: player, "volume_level": v_start},
        )
        if content_id := self.opt(CONF_MEDIA_CONTENT_ID):
            await self._call(
                "media_player",
                "play_media",
                {
                    ATTR_ENTITY_ID: player,
                    "media_content_id": content_id,
                    "media_content_type": self.opt(CONF_MEDIA_CONTENT_TYPE) or "music",
                },
            )
        elif source := self.opt(CONF_SOURCE):
            await self._call(
                "media_player",
                "select_source",
                {ATTR_ENTITY_ID: player, "source": source},
            )
        else:
            await self._call("media_player", "media_play", {ATTR_ENTITY_ID: player})

        if ramp <= 0 or v_end <= v_start:
            if v_end != v_start:
                await self._call(
                    "media_player",
                    "volume_set",
                    {ATTR_ENTITY_ID: player, "volume_level": v_end},
                )
            return
        steps = max(1, int(ramp // VOLUME_STEP_SECONDS))
        for i in range(1, steps + 1):
            await asyncio.sleep(ramp / steps)
            level = round(v_start + (v_end - v_start) * i / steps, 3)
            await self._call(
                "media_player",
                "volume_set",
                {ATTR_ENTITY_ID: player, "volume_level": level},
            )

    @callback
    def _handle_auto_dismiss(self, _now: datetime) -> None:
        self._auto_dismiss = None
        self.hass.async_create_task(self.async_dismiss())

    # ------------------------------------------------------------------
    # Snooze / dismiss
    # ------------------------------------------------------------------
    async def async_snooze(self) -> None:
        """Pause playback and ring again after the snooze period."""
        if self.status != STATUS_RINGING:
            return
        self._cancel_task("_volume_task")
        self._cancel_auto_dismiss()
        await self._pause_media()
        self.status = STATUS_SNOOZED
        self.snooze_until = dt_util.now() + timedelta(
            minutes=float(self.opt(CONF_SNOOZE))
        )
        self.hass.bus.async_fire(
            EVENT_SNOOZED,
            {**self._event_data(), "snooze_until": self.snooze_until.isoformat()},
        )
        self.reschedule()

    async def async_dismiss(self) -> None:
        """Stop the alarm and arm the next occurrence."""
        if self.status == STATUS_IDLE:
            return
        was = self.status
        self._cancel_task("_volume_task")
        self._cancel_task("_light_task")
        self._cancel_auto_dismiss()
        if was in (STATUS_RINGING, STATUS_SNOOZED):
            await self._pause_media()
        self.status = STATUS_IDLE
        self.snooze_until = None
        if was == STATUS_PRE_WAKE and self.is_repeating:
            # Dismissed during the fade: skip this occurrence only
            self._skipped = self.next_alarm
        elif not self.is_repeating:
            # One-shot alarms switch themselves off once handled
            self.enabled = False
            self._save()
        self.hass.bus.async_fire(EVENT_DISMISSED, self._event_data())
        self.reschedule()

    async def _pause_media(self) -> None:
        if not (player := self.media_player):
            return
        state = self.hass.states.get(player)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        await self._call("media_player", "media_pause", {ATTR_ENTITY_ID: player})

    # ------------------------------------------------------------------
    async def _call(self, domain: str, service: str, data: dict[str, Any]) -> None:
        """Call a service, logging instead of raising so a bad device can't stop the alarm."""
        try:
            await self.hass.services.async_call(domain, service, data, blocking=True)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "%s: %s.%s failed for %s: %s",
                self.entry.title,
                domain,
                service,
                data.get(ATTR_ENTITY_ID),
                err,
            )
