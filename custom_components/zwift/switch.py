"""Zwift switch platform."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zwift switches from a config entry."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    entities = [
        ZwiftPollingSwitch(coordinator.player, coordinator, entry)
        for coordinator in coordinators.values()
    ]
    async_add_entities(entities)


class ZwiftPollingSwitch(SwitchEntity):
    """Switch to enable or disable Zwift update polling for a player."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "enable_polling"

    def __init__(self, player, coordinator, entry):
        self._player = player
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"zwift_polling_{player.player_id}"

    @property
    def icon(self):
        return "mdi:update" if self.is_on else "mdi:cancel"

    @property
    def device_info(self) -> DeviceInfo:
        return self._player.device_info

    @property
    def is_on(self):
        return self._coordinator.update_interval is not None

    async def async_turn_on(self, **kwargs):
        await self._coordinator.turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._coordinator.turn_off()
        self.async_write_ha_state()
