"""Zwift image platform — exposes player profile picture."""

from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import _LOGGER, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zwift image entities from a config entry."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    entities = [
        ZwiftProfileImageEntity(coordinator, hass, coordinator.player, entry)
        for coordinator in coordinators.values()
    ]
    async_add_entities(entities, True)


class ZwiftProfileImageEntity(CoordinatorEntity, ImageEntity):
    """Image entity for a Zwift player's profile picture."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, hass, player, entry):
        """Initialize the image entity."""
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self._player = player
        self._attr_unique_id = f"zwift_profile_image_{player.player_id}"
        self._current_url = None
        self._cached_image = None

    @property
    def device_info(self):
        return self._player.device_info

    @property
    def name(self):
        return "Profile Picture"

    @property
    def extra_state_attributes(self):
        """Return the original image URL as an attribute."""
        url = self._player.image_src
        if url:
            return {"url": url}
        return None

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        url = self._player.image_src
        if not url:
            return None

        # Re-fetch only when URL changes
        if url != self._current_url:
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(url) as resp:
                    if resp.status == 200:
                        self._cached_image = await resp.read()
                        self._current_url = url
                        self._attr_image_last_updated = datetime.now()
                    else:
                        _LOGGER.warning(
                            "Failed to fetch Zwift profile image: %s",
                            resp.status,
                        )
            except Exception:
                _LOGGER.exception("Error fetching Zwift profile image")

        return self._cached_image
