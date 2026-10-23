"""Card loading: dashboard resource in www, with fallback."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sunrise_alarm import card_loader
from custom_components.sunrise_alarm.const import DOMAIN, VERSION


class FakeResources:
    """Minimal stand-in for Lovelace's storage-mode resource collection."""

    def __init__(self, items=None):
        self.loaded = False
        self.items = {i["id"]: i for i in (items or [])}

    async def async_load(self):
        self.loaded = True

    def async_items(self):
        return list(self.items.values())

    async def async_create_item(self, data):
        item = {"id": f"id{len(self.items)}", "type": data["res_type"], "url": data["url"]}
        self.items[item["id"]] = item
        return item

    async def async_update_item(self, item_id, data):
        self.items[item_id] = {**self.items[item_id], **data}

    async def async_delete_item(self, item_id):
        del self.items[item_id]


class FakeLovelace:
    def __init__(self, resources):
        self.resources = resources


async def test_registers_resource_when_www_exists(hass: HomeAssistant, http_stub, mock_frontend):
    www = Path(hass.config.path("www"))
    www.mkdir(exist_ok=True)
    res = FakeResources([{"id": "old", "type": "module", "url": f"/local/{DOMAIN}/sunrise-alarm-card.js?v=0.2.0"},
                         {"id": "other", "type": "module", "url": "/local/other.js"}])
    hass.data["lovelace"] = FakeLovelace(res)

    await card_loader.async_setup_card(hass)

    assert (www / DOMAIN / "sunrise-alarm-card.js").read_bytes() == card_loader.SOURCE.read_bytes()
    assert res.items["old"]["url"] == f"/local/{DOMAIN}/sunrise-alarm-card.js?v={VERSION}"  # updated, not duplicated
    assert len(res.items) == 2
    mock_frontend.assert_not_called()  # no fallback needed


async def test_creates_resource_once(hass, http_stub, mock_frontend):
    Path(hass.config.path("www")).mkdir(exist_ok=True)
    res = FakeResources()
    hass.data["lovelace"] = FakeLovelace(res)
    await card_loader.async_setup_card(hass)
    await card_loader.async_setup_card(hass)
    assert [i["url"] for i in res.items.values()] == [f"/local/{DOMAIN}/sunrise-alarm-card.js?v={VERSION}"]


async def test_fallback_when_www_just_created(hass, http_stub, mock_frontend):
    """/local isn't served until the next restart, so serve the card ourselves this time."""
    www = Path(hass.config.path("www"))
    assert not www.exists()
    hass.data["lovelace"] = FakeLovelace(FakeResources())
    await card_loader.async_setup_card(hass)
    assert (www / DOMAIN / "sunrise-alarm-card.js").exists()
    mock_frontend.assert_called_once()


async def test_fallback_when_resources_in_yaml(hass, http_stub, mock_frontend):
    Path(hass.config.path("www")).mkdir(exist_ok=True)

    class YamlResources:
        loaded = True

        def async_items(self):
            return []

    hass.data["lovelace"] = FakeLovelace(YamlResources())
    await card_loader.async_setup_card(hass)
    mock_frontend.assert_called_once()


async def test_cleanup_after_last_alarm_removed(hass, http_stub, mock_frontend):
    Path(hass.config.path("www")).mkdir(exist_ok=True)
    res = FakeResources()
    hass.data["lovelace"] = FakeLovelace(res)
    await hass.config.async_set_time_zone("America/Detroit")
    entries = []
    for name in ("A", "B"):
        e = MockConfigEntry(domain=DOMAIN, title=name, data={"name": name})
        e.add_to_hass(hass)
        entries.append(e)
    assert await hass.config_entries.async_setup(entries[0].entry_id)
    await hass.async_block_till_done()
    assert len(res.items) == 1

    await hass.config_entries.async_remove(entries[0].entry_id)
    assert len(res.items) == 1  # another alarm still uses the card
    await hass.config_entries.async_remove(entries[1].entry_id)
    await hass.async_block_till_done()
    assert not res.items
    assert not Path(hass.config.path("www", DOMAIN)).exists()
