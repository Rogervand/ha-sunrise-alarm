"""Fixtures."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunrise_alarm.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    return


@pytest.fixture(autouse=True)
def mock_frontend():
    """Skip real frontend/http/sonos setup; record the extra JS URL."""
    with (
        patch("custom_components.sunrise_alarm.add_extra_js_url") as js,
        patch(
            "homeassistant.loader.Integration.dependencies",
            new_callable=lambda: property(
                lambda self: []
                if self.domain == DOMAIN
                else self.manifest.get("dependencies", [])
            ),
        ),
        patch(
            "homeassistant.loader.Integration.after_dependencies",
            new_callable=lambda: property(
                lambda self: []
                if self.domain == DOMAIN
                else self.manifest.get("after_dependencies", [])
            ),
        ),
    ):
        yield js


@pytest.fixture
async def http_stub(hass: HomeAssistant):
    """Give hass a fake http server with a static path registrar."""

    class _Http:
        def __init__(self):
            self.paths = []

        async def async_register_static_paths(self, configs):
            self.paths.extend(configs)

    hass.http = _Http()
    return hass.http


@pytest.fixture
def options() -> dict:
    """Entry options (empty for 0.2 alarms)."""
    return {}


@pytest.fixture
async def setup_alarm(hass: HomeAssistant, http_stub, options):
    """Create and load one alarm."""
    await hass.config.async_set_time_zone("America/Detroit")
    entry = MockConfigEntry(
        domain=DOMAIN, title="Bedroom", data={"name": "Bedroom"}, options=options
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
