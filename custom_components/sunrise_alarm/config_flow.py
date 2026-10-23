"""Config flow for Sunrise Alarm Clock: just a name; everything else is set on the card."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from .const import DOMAIN


class SunriseAlarmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create an alarm."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name the alarm."""
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            self._async_abort_entries_match({CONF_NAME: name})
            return self.async_create_entry(title=name, data={CONF_NAME: name})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default="Bedroom"): str}),
        )
