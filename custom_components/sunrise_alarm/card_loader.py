"""Get the dashboard card into the browser reliably, including right after a restart.

Home Assistant's frontend reads the list of extra scripts once, when a page
opens. A page opened while Home Assistant is still starting (before this
integration has loaded, e.g. while it waits on other integrations) never gets
the card script and shows "Configuration error" until it is reloaded.

To avoid that, the card is copied to ``<config>/www/sunrise_alarm/`` and
registered as a dashboard resource at ``/local/sunrise_alarm/...``. Both the
resource list and ``/local`` are available from the start of every boot, so
the card loads with the page no matter how long this integration takes.

When that isn't possible (resources managed in YAML, or the ``www`` folder was
only just created and ``/local`` isn't served until the next restart) the
integration falls back to serving the card itself.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, CARD_URL, CARD_URL_BASE, DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

SOURCE = Path(__file__).parent / "frontend" / CARD_FILENAME
LOCAL_PATH = f"/local/{DOMAIN}/{CARD_FILENAME}"
LOCAL_URL = f"{LOCAL_PATH}?v={VERSION}"


def _install_file(www: Path) -> bool:
    """Copy the card into www/sunrise_alarm/. Return True if www already existed."""
    existed = www.is_dir()
    target = www / DOMAIN / CARD_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_bytes() != SOURCE.read_bytes():
        shutil.copyfile(SOURCE, target)
    return existed


def _resources(hass: HomeAssistant):
    """Return the Lovelace resource collection if it's editable (storage mode)."""
    data = hass.data.get("lovelace")
    resources = getattr(data, "resources", None)
    if resources is None and isinstance(data, dict):
        resources = data.get("resources")
    if resources is None or not hasattr(resources, "async_create_item"):
        return None
    return resources


async def _ensure_resource(hass: HomeAssistant) -> bool:
    """Add or update our dashboard resource. Return True if it's registered."""
    resources = _resources(hass)
    if resources is None:
        return False
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True
    for item in resources.async_items():
        url = item.get("url", "")
        if url.split("?")[0] == LOCAL_PATH:
            if url != LOCAL_URL:
                await resources.async_update_item(item["id"], {"url": LOCAL_URL})
            return True
    await resources.async_create_item({"res_type": "module", "url": LOCAL_URL})
    return True


async def async_setup_card(hass: HomeAssistant) -> None:
    """Make the card available to dashboards."""
    # The integration always serves the card too; the fallback below uses it
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_BASE, str(SOURCE.parent), False)]
    )

    local_served = False
    resource_ok = False
    try:
        local_served = await hass.async_add_executor_job(
            _install_file, Path(hass.config.path("www"))
        )
        resource_ok = await _ensure_resource(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Couldn't register the Sunrise Alarm card as a dashboard resource; "
            "falling back to loading it from the integration",
            exc_info=True,
        )

    if not (local_served and resource_ok):
        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")


async def async_remove_card(hass: HomeAssistant) -> None:
    """Remove the resource and copied file once the last alarm is deleted."""
    try:
        if (resources := _resources(hass)) is not None:
            if not getattr(resources, "loaded", True):
                await resources.async_load()
                resources.loaded = True
            for item in list(resources.async_items()):
                if item.get("url", "").split("?")[0] == LOCAL_PATH:
                    await resources.async_delete_item(item["id"])
        folder = Path(hass.config.path("www", DOMAIN))
        await hass.async_add_executor_job(shutil.rmtree, folder, True)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Card cleanup failed", exc_info=True)
