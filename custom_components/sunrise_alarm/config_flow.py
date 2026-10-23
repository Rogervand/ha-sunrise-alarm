"""Config and options flow for Sunrise Alarm Clock."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

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
)

MEDIA_TYPES = ["music", "playlist", "favorite_item_id", "url", "channel", "podcast"]


def _minutes(max_value: int, step: float = 1) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            max=max_value,
            step=step,
            unit_of_measurement="min",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _percent() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            max=100,
            step=1,
            unit_of_measurement="%",
            mode=selector.NumberSelectorMode.SLIDER,
        )
    )


def _kelvin() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1800,
            max=6500,
            step=100,
            unit_of_measurement="K",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _optional(key: str, current: dict[str, Any]) -> vol.Optional:
    """Optional key that pre-fills only when a value exists (so it can be cleared)."""
    if current.get(key) not in (None, "", []):
        return vol.Optional(key, description={"suggested_value": current[key]})
    return vol.Optional(key)


def settings_schema(current: dict[str, Any]) -> vol.Schema:
    """Shared schema for wake actions; ``current`` supplies defaults."""

    def d(key: str) -> Any:
        return current.get(key, DEFAULTS.get(key))

    return vol.Schema(
        {
            _optional(CONF_MEDIA_PLAYER, current): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player")
            ),
            _optional(CONF_SOURCE, current): selector.TextSelector(),
            _optional(CONF_MEDIA_CONTENT_ID, current): selector.TextSelector(),
            vol.Required(
                CONF_MEDIA_CONTENT_TYPE, default=d(CONF_MEDIA_CONTENT_TYPE)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=MEDIA_TYPES,
                    custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="media_content_type",
                )
            ),
            vol.Required(CONF_VOLUME_START, default=d(CONF_VOLUME_START)): _percent(),
            vol.Required(CONF_VOLUME_END, default=d(CONF_VOLUME_END)): _percent(),
            vol.Required(CONF_VOLUME_RAMP, default=d(CONF_VOLUME_RAMP)): _minutes(60),
            _optional(CONF_LIGHTS, current): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
            vol.Required(CONF_LIGHT_FADE, default=d(CONF_LIGHT_FADE)): _minutes(90),
            vol.Required(CONF_KELVIN_START, default=d(CONF_KELVIN_START)): _kelvin(),
            vol.Required(CONF_KELVIN_END, default=d(CONF_KELVIN_END)): _kelvin(),
            vol.Required(CONF_SNOOZE, default=d(CONF_SNOOZE)): _minutes(60),
            vol.Required(CONF_AUTO_DISMISS, default=d(CONF_AUTO_DISMISS)): _minutes(
                240
            ),
        }
    )


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not user_input.get(CONF_MEDIA_PLAYER) and not user_input.get(CONF_LIGHTS):
        errors["base"] = "nothing_to_do"
    if user_input.get(CONF_VOLUME_END, 0) < user_input.get(CONF_VOLUME_START, 0):
        errors[CONF_VOLUME_END] = "volume_order"
    return errors


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    """Store whole numbers as ints and drop empty optionals."""
    out: dict[str, Any] = {}
    for key, value in user_input.items():
        if value in (None, "", []):
            continue
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        out[key] = value
    return out


class SunriseAlarmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create an alarm."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name the alarm and pick its wake actions."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                name = user_input.pop(CONF_NAME)
                self._async_abort_entries_match({CONF_NAME: name})
                return self.async_create_entry(
                    title=name, data={CONF_NAME: name}, options=_clean(user_input)
                )

        current = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=current.get(CONF_NAME, "Bedroom alarm")
                ): str
            }
        ).extend(settings_schema(current).schema)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return SunriseAlarmOptionsFlow()


class SunriseAlarmOptionsFlow(OptionsFlow):
    """Edit wake actions of an existing alarm."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(data=_clean(user_input))
        current = user_input or dict(self.config_entry.options)
        return self.async_show_form(
            step_id="init", data_schema=settings_schema(current), errors=errors
        )
