"""The Zwift integration."""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er, issue_registry as ir

from .const import (
    _LOGGER,
    CONF_INCLUDE_SELF,
    CONF_PLAYERS,
    DOMAIN,
)
from .coordinator import ZwiftPlayerCoordinator
from .zwift_data import ZwiftData

PLATFORMS = ["image", "light", "number", "sensor", "switch"]

DEFAULT_SELF_INTERVAL = 15
DEFAULT_OTHER_INTERVAL = 60

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_PLAYERS, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_INCLUDE_SELF, default=True): cv.boolean,
                vol.Optional(CONF_NAME, default="Zwift"): cv.string,
            },
            # Silently drop unrecognized/legacy keys (e.g. the old sensor-platform
            # schema's `update_interval`) instead of failing validation for the whole
            # domain — a hard failure here takes down every existing config entry too,
            # not just the YAML import.
            extra=vol.REMOVE_EXTRA,
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Zwift component from YAML."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=config[DOMAIN],
            )
        )
        ir.async_create_issue(
            hass,
            DOMAIN,
            "deprecated_yaml_domain_config",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_yaml_domain_config",
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Zwift from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    # Players and include_self live in options so they can be changed later
    players = entry.options.get(CONF_PLAYERS, entry.data.get(CONF_PLAYERS, []))
    include_self = entry.options.get(CONF_INCLUDE_SELF, entry.data.get(CONF_INCLUDE_SELF, True))

    zwift_data = ZwiftData(username, password, players, hass)
    try:
        await zwift_data.connect()
    except Exception:
        _LOGGER.exception("Could not connect to Zwift")
        return False

    if include_self:
        zwift_data.add_tracked_player(zwift_data.profile.get("id"))

    self_player_id = zwift_data.profile.get("id") if zwift_data.profile else None

    coordinators = {}
    for player_id in zwift_data.players:
        default_interval = DEFAULT_SELF_INTERVAL if player_id == self_player_id else DEFAULT_OTHER_INTERVAL
        coordinator = ZwiftPlayerCoordinator(hass, entry, zwift_data, player_id, default_interval)
        await coordinator.async_config_entry_first_refresh()
        coordinators[player_id] = coordinator

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "zwift_data": zwift_data,
        "coordinators": coordinators,
        "self_player_id": self_player_id,
        "structural_options": {
            CONF_PLAYERS: players,
            CONF_INCLUDE_SELF: include_self,
        },
    }

    # Remove devices for players that are no longer tracked
    current_player_ids = {(DOMAIN, str(pid)) for pid in zwift_data.players}
    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if not device.identifiers & current_player_ids:
            device_registry.async_remove_device(device.id)

    # Remove old "Update" button entities from previous versions, regardless of
    # whether their player is still tracked
    entity_registry = er.async_get(hass)
    for entity in list(entity_registry.entities.values()):
        if (
            entity.platform == DOMAIN
            and entity.domain == "button"
            and entity.unique_id.startswith("zwift_update_")
        ):
            entity_registry.async_remove(entity.entity_id)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Reload only when structural options (player list, include_self) change."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if entry_data is None:
        return
    prev = entry_data.get("structural_options", {})
    new_players = entry.options.get(CONF_PLAYERS, entry.data.get(CONF_PLAYERS, []))
    new_include_self = entry.options.get(CONF_INCLUDE_SELF, entry.data.get(CONF_INCLUDE_SELF, True))
    if prev.get(CONF_PLAYERS) != new_players or prev.get(CONF_INCLUDE_SELF) != new_include_self:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
