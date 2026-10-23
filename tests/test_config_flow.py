"""Config flow tests."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.sunrise_alarm.const import DOMAIN


async def test_create(hass, http_stub):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    r = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": " Kids room "})
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["title"] == "Kids room"
    await hass.async_block_till_done()
    assert hass.states.get("sensor.kids_room_next_alarm") is not None

    again = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    r = await hass.config_entries.flow.async_configure(again["flow_id"], {"name": "Kids room"})
    assert r["type"] is FlowResultType.ABORT
