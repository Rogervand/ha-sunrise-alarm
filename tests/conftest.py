"""Fixtures."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunrise_alarm.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    return


@pytest.fixture(autouse=True)
def mock_frontend():
    """Skip real frontend/http setup; just record the extra JS URL."""
    with (
        patch(
            "custom_components.sunrise_alarm.add_extra_js_url"
        ) as js,
        patch(
            "homeassistant.loader.Integration.dependencies",
            new_callable=lambda: property(lambda self: [] if self.domain == DOMAIN else self.manifest.get("dependencies", [])),
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


OPTIONS = {
    "media_player": "media_player.bedroom",
    "media_content_id": "FV:2/5",
    "media_content_type": "favorite_item_id",
    "volume_start": 5,
    "volume_end": 25,
    "volume_ramp_minutes": 2,
    "lights": ["light.bedside"],
    "light_fade_minutes": 10,
    "kelvin_start": 2200,
    "kelvin_end": 4000,
    "snooze_minutes": 9,
    "auto_dismiss_minutes": 30,
}


@pytest.fixture
def options() -> dict:
    """Default options (copy)."""
    return dict(OPTIONS)


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
