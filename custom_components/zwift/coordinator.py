"""Zwift per-player data update coordinator."""

from datetime import timedelta

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import _LOGGER, DOMAIN



def _player_interval_key(player_id):
    return f"player_{player_id}_interval"


def _player_polling_key(player_id):
    return f"player_{player_id}_polling"


class ZwiftPlayerCoordinator(DataUpdateCoordinator):
    """Coordinator for a single Zwift player's data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, zwift_data, player_id, default_interval):
        """Initialize the coordinator."""

        interval = entry.options.get(_player_interval_key(player_id), default_interval)
        polling_enabled = entry.options.get(_player_polling_key(player_id), True)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{player_id}",
            update_interval=timedelta(seconds=interval) if polling_enabled else None,
        )
        self.zwift_data = zwift_data
        self.player_id = player_id
        self._configured_interval = interval
        self._entry = entry

    async def turn_on(self):
        """Enable polling with the currently configured interval."""
        self.update_interval = timedelta(seconds=self.configured_interval)
        await self.async_request_refresh()
        self._save_to_options(True, self._configured_interval)

    def turn_off(self):
        """Disable polling."""
        self.update_interval = None
        self._save_to_options(False, self._configured_interval)

    def _save_to_options(self, enabled, interval):
        """Persist polling state to config entry options."""
        new_options = {
            **self._entry.options,
            _player_polling_key(self.player_id): enabled,
            _player_interval_key(self.player_id): interval,
        }
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)

    @property
    def configured_interval(self):
        """Return the configured offline polling interval in seconds."""
        return self._configured_interval

    @configured_interval.setter
    def configured_interval(self, value):
        """Set the configured offline polling interval and apply it."""
        self._configured_interval = value
        self._save_to_options(self.update_interval is not None, value)
        # Apply immediately if polling is enabled and player is offline
        if self.update_interval is not None:
            self.update_interval = timedelta(seconds=value)

    @property
    def player(self):
        """Return the ZwiftPlayerData for this coordinator's player."""
        return self.zwift_data.players[self.player_id]

    async def _async_update_data(self):
        """Fetch data from Zwift for this player."""
        if not self.zwift_data.is_connected:
            await self.zwift_data.connect()

        await self.zwift_data.update_player(self.player_id)

        player = self.player

        # Handle device name changes
        if player.device_name_changed:
            player.acknowledge_device_name_change()
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, str(self.player_id))}
            )
            if device:
                device_registry.async_update_device(
                    device.id, name=player.last_device_name
                )

        # Adjust polling interval based on online status
        # (only when polling is enabled — update_interval=None means disabled)
        if self.update_interval is not None:
            if player.online:
                self.update_interval = self.zwift_data.online_update_interval
            else:
                self.update_interval = timedelta(seconds=self._configured_interval)

        return player
