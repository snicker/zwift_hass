"""Zwift sensor platform."""

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME, EntityCategory, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    _LOGGER,
    CONF_INCLUDE_SELF,
    CONF_PLAYERS,
    DEFAULT_NAME,
    DOMAIN,
    POWER_ZONE_OPTIONS,
    SENSOR_TYPES,
    SPORT_OPTIONS,
    ZWIFT_IGNORED_PROFILE_ATTRIBUTES,
)

# Legacy `sensor: - platform: zwift` YAML schema, kept only so existing users are
# migrated automatically instead of needing to hand-edit configuration.yaml.
# `extra=vol.REMOVE_EXTRA` drops stray old keys (e.g. `update_interval`) instead of
# failing validation for the whole platform.
PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PLAYERS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_INCLUDE_SELF, default=True): cv.boolean,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    },
    extra=vol.REMOVE_EXTRA,
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Forward legacy `sensor: - platform: zwift` YAML into the config flow import step."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data={
                CONF_USERNAME: config[CONF_USERNAME],
                CONF_PASSWORD: config[CONF_PASSWORD],
                CONF_PLAYERS: config.get(CONF_PLAYERS, []),
                CONF_INCLUDE_SELF: config.get(CONF_INCLUDE_SELF, True),
                CONF_NAME: config.get(CONF_NAME, DEFAULT_NAME),
            },
        )
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        "deprecated_yaml_sensor_platform",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="deprecated_yaml_sensor_platform",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zwift sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinators = entry_data["coordinators"]
    self_player_id = entry_data.get("self_player_id")

    class_map = {
        "ZwiftOnlineSensorEntity": ZwiftOnlineSensorEntity,
        "ZwiftPowerZoneSensorEntity": ZwiftPowerZoneSensorEntity,
        "ZwiftSportSensorEntity": ZwiftSportSensorEntity,
    }

    entities = []
    for player_id, coordinator in coordinators.items():
        player = coordinator.player
        for variable, config in SENSOR_TYPES.items():
            if config.get("self_only") and player_id != self_player_id:
                continue
            entity_class = class_map.get(config.get("entity_class"), ZwiftSensorEntity)
            entities.append(entity_class(coordinator, player, variable, entry))

    async_add_entities(entities, True)


class ZwiftSensorEntity(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, player, sensor_type, entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._player = player
        self._type = sensor_type
        self._sensor_config = SENSOR_TYPES[sensor_type]
        self._entry = entry
        base_name = entry.data.get(CONF_NAME, DEFAULT_NAME)
        self._attr_unique_id = f"{base_name}_{self._sensor_config['name']}_{self._player.player_id}".replace(" ", "").lower()

    @property
    def device_info(self):
        return self._player.device_info

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._sensor_config.get("name")

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return getattr(self._player, self._type)

    @property
    def native_unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._sensor_config.get("unit")

    @property
    def suggested_unit_of_measurement(self):
        """Return suggested unit based on the account owner's metric preference."""
        use_metric = self.coordinator.zwift_data.is_metric
        if use_metric:
            return self._sensor_config.get("suggested_unit_metric")
        return self._sensor_config.get("suggested_unit_imperial")

    @property
    def icon(self):
        return self._sensor_config.get("icon")

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._sensor_config.get("device_class")

    @property
    def entity_category(self):
        """Return the entity category."""
        category = self._sensor_config.get("entity_category")
        if category:
            return EntityCategory(category)
        return None

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return self._sensor_config.get("state_class")


class ZwiftPowerZoneSensorEntity(ZwiftSensorEntity):
    _attr_translation_key = "powerzonename"
    _attr_options = POWER_ZONE_OPTIONS
    _attr_device_class = SensorDeviceClass.ENUM

class ZwiftSportSensorEntity(ZwiftSensorEntity):
    _attr_translation_key = "sport"
    _attr_options = SPORT_OPTIONS
    _attr_device_class = SensorDeviceClass.ENUM

    @property
    def icon(self):
        if self.native_value == "running":
            return "mdi:run"
        return "mdi:bike"

class ZwiftOnlineSensorEntity(ZwiftSensorEntity, BinarySensorEntity):
    _unrecorded_attributes = frozenset({MATCH_ALL})

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._type != "online":
            return None
        p = self._player.player_profile
        return {
            k: p[k]
            for k in p
            if k not in ZWIFT_IGNORED_PROFILE_ATTRIBUTES
        }

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._player.online
