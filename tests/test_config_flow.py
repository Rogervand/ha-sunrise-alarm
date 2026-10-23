"""Config flow tests."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.sunrise_alarm.const import DOMAIN


async def test_create_and_validate(hass, http_stub):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    base = {"name": "Bedroom", "media_content_type": "music", "volume_start": 5, "volume_end": 30,
            "volume_ramp_minutes": 5, "light_fade_minutes": 15, "kelvin_start": 2200,
            "kelvin_end": 4000, "snooze_minutes": 9, "auto_dismiss_minutes": 30}

    r = await hass.config_entries.flow.async_configure(result["flow_id"], dict(base))
    assert r["errors"] == {"base": "nothing_to_do"}

    r = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**base, "media_player": "media_player.x", "volume_start": 50, "volume_end": 10}
    )
    assert r["errors"] == {"volume_end": "volume_order"}

    r = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**base, "media_player": "media_player.bedroom", "volume_ramp_minutes": 2.0}
    )
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["title"] == "Bedroom"
    assert r["options"]["volume_ramp_minutes"] == 2
    assert isinstance(r["options"]["volume_ramp_minutes"], int)
    await hass.async_block_till_done()

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    o = await hass.config_entries.options.async_init(entry.entry_id)
    o = await hass.config_entries.options.async_configure(
        o["flow_id"], {**{k: v for k, v in base.items() if k != "name"}, "lights": ["light.a"], "light_fade_minutes": 20}
    )
    assert o["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["lights"] == ["light.a"]
    assert "media_player" not in entry.options  # cleared
    assert hass.states.get("sensor.bedroom_next_alarm").attributes["light_fade_minutes"] == 20
