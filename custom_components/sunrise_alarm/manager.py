"""Alarm state, scheduling and the wake-up ramp."""

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
    DEFAULT_SETTINGS,
    DOMAIN,
    EVENT_STARTED,
    EVENT_STOPPED,
    SET_BRIGHTNESS,
    SET_FAVORITE_ID,
    SET_FAVORITE_NAME,
    SET_LIGHTS,
    SET_RAMP,
    SET_SPEAKER,
    SET_VOLUME_END,
    SET_VOLUME_START,
    STATUS_IDLE,
    STATUS_WAKING,
    STEP_SECONDS,
    STORAGE_VERSION,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIME = time(7, 0)
DEFAULT_DAYS = [0, 1, 2, 3, 4]


def _settings_from_v1_options(options: dict[str, Any]) -> dict[str, Any]:
    """Carry settings over from a 0.1.x alarm, where they lived in entry options."""
    out: dict[str, Any] = {}
    if player := options.get("media_player"):
        out[SET_SPEAKER] = player
    if options.get("media_content_type") == "favorite_item_id" and options.get(
        "media_content_id"
    ):
        out[SET_FAVORITE_ID] = options["media_content_id"]
    for key in (SET_VOLUME_START, SET_VOLUME_END, SET_LIGHTS):
        if key in options:
            out[key] = options[key]
    if ramp := options.get("light_fade_minutes") or options.get("volume_ramp_minutes"):
        out[SET_RAMP] = int(ramp)
    return out


class AlarmManager:
    """Owns one alarm: its stored settings, timer and wake-up ramp."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )

        self.alarm_time: time = DEFAULT_TIME
        self.days: set[int] = set(DEFAULT_DAYS)
        self.enabled: bool = True
        self.settings: dict[str, Any] = dict(DEFAULT_SETTINGS)

        self.status: str = STATUS_IDLE
        self.next_alarm: datetime | None = None
        self.last_started: datetime | None = None

        self._listeners: list[Callable[[], None]] = []
        self._timer: CALLBACK_TYPE | None = None
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    @property
    def day_names(self) -> list[str]:
        """Selected weekdays as short names, Monday first."""
        return [WEEKDAYS[d] for d in sorted(self.days)]

    @property
    def is_repeating(self) -> bool:
        """True when at least one weekday is selected."""
        return bool(self.days)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_load(self) -> None:
        """Load stored state and arm the next alarm."""
        stored = await self._store.async_load()
        if stored is not None:
            try:
                self.alarm_time = time.fromisoformat(stored["time"])
            except (KeyError, ValueError):
                self.alarm_time = DEFAULT_TIME
            self.days = {
                WEEKDAYS.index(d) for d in stored.get("days", []) if d in WEEKDAYS
            }
            self.enabled = bool(stored.get("enabled", True))
        if stored is not None and "settings" in stored:
            self.settings.update(stored["settings"])
        elif self.entry.options:
            self.settings.update(_settings_from_v1_options(dict(self.entry.options)))
            self._save()
        self.reschedule()

    async def async_unload(self) -> None:
        """Cancel the timer and any ramp in progress."""
        self._cancel_timer()
        self._cancel_task()

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(
            lambda: {
                "time": self.alarm_time.strftime("%H:%M"),
                "days": self.day_names,
                "enabled": self.enabled,
                "settings": self.settings,
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
    # Changes from the card, entities and services
    # ------------------------------------------------------------------
    @callback
    def update(
        self,
        *,
        alarm_time: time | None = None,
        days: list[str] | None = None,
        enabled: bool | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        """Apply any combination of changes, then save and re-arm once."""
        if alarm_time is not None:
            self.alarm_time = alarm_time.replace(second=0, microsecond=0)
        if days is not None:
            self.days = {WEEKDAYS.index(d) for d in days if d in WEEKDAYS}
        if enabled is not None:
            self.enabled = enabled
        if settings:
            self.settings.update(settings)
        self._save()
        self.reschedule()

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    def compute_next(self, now: datetime) -> datetime | None:
        """Return the next start time strictly after ``now``, or None."""
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
            # Normalise so a time skipped by DST resolves to a real instant
            candidate = dt_util.as_local(dt_util.as_utc(candidate))
            if candidate > local_now:
                return candidate
        return None

    @callback
    def reschedule(self) -> None:
        """Recompute the next alarm and arm the timer."""
        self._cancel_timer()
        self.next_alarm = self.compute_next(dt_util.now())
        if self.next_alarm is not None:
            self._timer = async_track_point_in_time(
                self.hass, self._handle_alarm, self.next_alarm
            )
        self._notify()

    @callback
    def _cancel_timer(self) -> None:
        if self._timer:
            self._timer()
            self._timer = None

    @callback
    def _cancel_task(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    def _event_data(self) -> dict[str, Any]:
        return {
            "config_entry_id": self.entry.entry_id,
            "name": self.entry.title,
            "alarm_time": self.alarm_time.strftime("%H:%M"),
        }

    # ------------------------------------------------------------------
    # Wake-up
    # ------------------------------------------------------------------
    @callback
    def _handle_alarm(self, _now: datetime) -> None:
        self._timer = None
        if not self.is_repeating:
            # One-time alarm: switch off once it has gone off
            self.enabled = False
            self._save()
        self.start()

    @callback
    def start(self) -> None:
        """Start the wake-up ramp now."""
        self._cancel_task()
        self.status = STATUS_WAKING
        self.last_started = dt_util.now()
        self.hass.bus.async_fire(EVENT_STARTED, self._event_data())
        self._task = self.entry.async_create_background_task(
            self.hass, self._run_ramp(), f"{DOMAIN} wake-up ramp"
        )
        self.reschedule()

    async def _run_ramp(self) -> None:
        """Bring lights from off to the target and volume from start to end together."""
        s = self.settings
        lights: list[str] = list(s.get(SET_LIGHTS) or [])
        target = int(s.get(SET_BRIGHTNESS) or 100)
        speaker: str | None = s.get(SET_SPEAKER)
        v_start = float(s.get(SET_VOLUME_START) or 0) / 100
        v_end = float(s.get(SET_VOLUME_END) or 0) / 100
        seconds = max(1, float(s.get(SET_RAMP) or 1)) * 60
        steps = max(1, int(seconds // STEP_SECONDS))
        step_len = seconds / steps

        try:
            if speaker:
                await self._start_music(speaker, v_start)
            for i in range(steps + 1):
                frac = i / steps
                if lights:
                    await self._set_lights(
                        lights, max(1, round(target * frac)), step_len if i else 1
                    )
                if speaker and i and v_end != v_start:
                    await self._call(
                        "media_player",
                        "volume_set",
                        {
                            ATTR_ENTITY_ID: speaker,
                            "volume_level": round(
                                v_start + (v_end - v_start) * frac, 3
                            ),
                        },
                    )
                if i < steps:
                    await asyncio.sleep(step_len)
        finally:
            if self._task is asyncio.current_task():
                self._task = None
                self.status = STATUS_IDLE
                self._notify()

    async def _start_music(self, speaker: str, volume: float) -> None:
        await self._call(
            "media_player",
            "volume_set",
            {ATTR_ENTITY_ID: speaker, "volume_level": volume},
        )
        if favorite := self.settings.get(SET_FAVORITE_ID):
            await self._call(
                "media_player",
                "play_media",
                {
                    ATTR_ENTITY_ID: speaker,
                    "media_content_id": favorite,
                    "media_content_type": "favorite_item_id",
                },
            )
        else:
            await self._call("media_player", "media_play", {ATTR_ENTITY_ID: speaker})

    async def _set_lights(self, lights: list[str], pct: int, transition: float) -> None:
        for light in lights:
            await self._call(
                "light",
                "turn_on",
                {
                    ATTR_ENTITY_ID: light,
                    "brightness_pct": pct,
                    "transition": round(transition, 1),
                },
            )

    async def async_stop(self) -> None:
        """Stop a wake-up in progress: pause the music, leave the lights as they are."""
        if self.status != STATUS_WAKING:
            return
        self._cancel_task()
        self.status = STATUS_IDLE
        if (speaker := self.settings.get(SET_SPEAKER)) and (
            state := self.hass.states.get(speaker)
        ):
            if state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                await self._call(
                    "media_player", "media_pause", {ATTR_ENTITY_ID: speaker}
                )
        self.hass.bus.async_fire(EVENT_STOPPED, self._event_data())
        self._notify()

    # ------------------------------------------------------------------
    async def _call(self, domain: str, service: str, data: dict[str, Any]) -> None:
        """Call a service; log failures so one bad device can't stop the rest."""
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

    @property
    def favorite_label(self) -> str | None:
        """Name of the chosen favorite, if known."""
        return self.settings.get(SET_FAVORITE_NAME) or self.settings.get(
            SET_FAVORITE_ID
        )
