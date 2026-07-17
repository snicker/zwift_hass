"""Zwift number platform — per-player update interval."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zwift number entities from a config entry."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    entities = [
        ZwiftUpdateIntervalNumber(coordinator.player, coordinator, entry)
        for coordinator in coordinators.values()
    ]
    async_add_entities(entities)


class ZwiftUpdateIntervalNumber(NumberEntity):
    """Number entity to configure the update interval for a player."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "update_interval"
    _attr_native_min_value = 10
    _attr_native_max_value = 3600
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, player, coordinator, entry):
        self._player = player
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"zwift_update_interval_{player.player_id}"

    @property
    def icon(self):
        return "mdi:timer-cog-outline"

    @property
    def device_info(self) -> DeviceInfo:
        return self._player.device_info

    @property
    def native_value(self):
        return self._coordinator.configured_interval

    async def async_set_native_value(self, value: float) -> None:
        """Update the polling interval."""
        self._coordinator.configured_interval = value
        self.async_write_ha_state()
