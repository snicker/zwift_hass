"""Zwift data fetching and player model."""

from datetime import timedelta

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

import custom_components.zwift.zwift_patch  # noqa: F401 — applies protobuf patch
from zwift import Client as ZwiftClient
from zwift.error import RequestException

from .const import (
    _LOGGER,
    DOMAIN,
    EVENT_ZWIFT_RIDE_ON,
    POWER_ZONES,
    POWER_ZONE_NEUROMUSCULAR,
    ZWIFT_WORLDS,
)


class ZwiftPlayerData:
    def __init__(self, player_id):
        self._player_id = player_id
        self.data = {}
        self.player_profile = {}
        self._last_device_name = None
        self._device_name_changed = False

    @property
    def player_id(self):
        return self._player_id

    @property
    def device_name_changed(self):
        """Return whether the device name has changed since last check."""
        return self._device_name_changed

    def acknowledge_device_name_change(self):
        """Clear the device name changed flag."""
        self._device_name_changed = False

    @property
    def last_device_name(self):
        """Return the most recent device name."""
        return self._last_device_name

    @property
    def friendly_player_id(self):
        first = self.player_profile.get("firstName", "")
        last = self.player_profile.get("lastName", "")
        full_name = f"{first} {last}".strip()
        return full_name or self.player_id

    @property
    def online(self):
        return self.data.get("online", False)

    @property
    def hr(self):
        return round(self.data.get("heartrate", 0.0), 0)

    @property
    def speed(self):
        return round(self.data.get("speed", 0.0), 0)

    @property
    def cadence(self):
        return round(self.data.get("cadence", 0.0), 0)

    @property
    def power(self):
        return round(self.data.get("power", 0.0), 0)

    @property
    def altitude(self):
        return round(self.data.get("altitude", 0.0), 1)

    @property
    def distance(self):
        return self.data.get("distance", 0.0)

    @property
    def gradient(self):
        return round(self.data.get("gradient", 0.0), 1)

    @property
    def level(self):
        return self.player_profile.get("playerLevel", None)

    @property
    def runlevel(self):
        return self.player_profile.get("runLevel", None)

    @property
    def cycleprogress(self):
        return self.player_profile.get("cycleProgress", None)

    @property
    def runprogress(self):
        return self.player_profile.get("runProgress", None)

    @property
    def totaldistance(self):
        return self.player_profile.get("totalDistance", None)

    @property
    def totaldistanceclimbed(self):
        return self.player_profile.get("totalDistanceClimbed", None)

    @property
    def totaltimeinminutes(self):
        return self.player_profile.get("totalTimeInMinutes", None)

    @property
    def totalgold(self):
        return self.player_profile.get("totalGold", None)

    @property
    def streakscurrentlength(self):
        return self.player_profile.get("streaksCurrentLength", None)

    @property
    def streaksmaxlength(self):
        return self.player_profile.get("streaksMaxLength", None)

    @property
    def racingscore(self):
        metrics = self.player_profile.get("competitionMetrics", {})
        return metrics.get("racingScore", None) if metrics else None

    @property
    def racingcategory(self):
        metrics = self.player_profile.get("competitionMetrics", {})
        if not metrics:
            return None
        if self.player_profile.get("male", True):
            return metrics.get("category", None)
        return metrics.get("categoryWomen", None)

    @property
    def ftp(self):
        return self.player_profile.get("ftp", None)

    @property
    def weight(self):
        return self.player_profile.get("weight", None)

    @property
    def height(self):
        return self.player_profile.get("height", None)

    @property
    def dob(self):
        dob_str = self.player_profile.get("dob", None)
        if dob_str:
            from datetime import datetime
            try:
                return datetime.strptime(dob_str, "%m/%d/%Y").date()
            except (ValueError, TypeError):
                return None
        return None

    @property
    def age(self):
        return self.player_profile.get("age", None)

    @property
    def createdon(self):
        created_str = self.player_profile.get("createdOn", None)
        if created_str:
            from datetime import datetime
            try:
                return datetime.fromisoformat(created_str)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def power_zone(self):
        """Return power zone info based on current power and FTP."""
        ftp = self.ftp
        power = self.power
        if not ftp or ftp == 0:
            return None
        ratio = power / ftp
        for threshold, zone, name, color in POWER_ZONES:
            if ratio < threshold:
                return (zone, name, color)
        return POWER_ZONE_NEUROMUSCULAR

    @property
    def powerzone(self):
        info = self.power_zone
        return info[0] if info else None

    @property
    def powerzonename(self):
        info = self.power_zone
        return info[1] if info else None

    @property
    def sport(self):
        activity = self.player_profile.get("latest_activity", {})
        sport = activity.get("sport", None)
        return sport.lower() if sport else None

    @property
    def image_src(self):
        return self.player_profile.get("imageSrc", None)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._player_id))},
            name=f"Zwift {self.friendly_player_id}",
            manufacturer="Zwift",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"https://www.zwift.com/athlete/{self._player_id}",
        )


class ZwiftData:
    """Representation of a Zwift client data collection object."""

    def __init__(self, username, password, players, hass):
        self._client = None
        self.username = username
        self.password = password
        self.hass = hass
        self.players = {}
        self._profile = None
        self.online_update_interval = timedelta(seconds=2)
        if players:
            for player_id in players:
                self.add_tracked_player(player_id)

    def add_tracked_player(self, player_id):
        if player_id:
            self.players[player_id] = ZwiftPlayerData(player_id)

    @property
    def any_players_online(self):
        return any(p.online for p in self.players.values())

    async def check_zwift_auth(self, client):
        token = await self.hass.async_add_executor_job(
            client.auth_token.fetch_token_data
        )
        if "error" in token:
            raise Exception(f"Zwift authorization failed: {token}")
        return True

    @property
    def is_metric(self):
        if self._profile:
            return self._profile.get("useMetric", False)
        return False

    async def connect(self):
        """Connect to the Zwift API and fetch the user profile."""
        client = ZwiftClient(self.username, self.password)
        if await self.check_zwift_auth(client):
            self._client = client
            self._profile = await self.hass.async_add_executor_job(
                self._get_self_profile
            )
            return self._client

    @property
    def profile(self):
        """Return the authenticated user's profile."""
        return self._profile

    @property
    def is_connected(self):
        """Return whether the client is connected."""
        return self._client is not None

    def _get_self_profile(self):
        return self._client.get_profile().profile

    async def update_player(self, player_id):
        """Update a single player (connects world internally)."""
        await self.hass.async_add_executor_job(
            self._update_player_sync, player_id
        )

    def _update_player_sync(self, player_id):
        """Synchronous update for a single player."""
        if self._client:
            world = self._client.get_world(1)
            self._update_player(player_id, world)

    def _update_player(self, player_id, world):
        """Fetch and update data for a single player."""
        try:
            player_profile = self._fetch_player_profile(player_id)
            data = {
                "total_experience": int(player_profile.get("totalExperiencePoints")),
                "level": player_profile["playerLevel"],
            }
            if player_profile.get("riding"):
                ride_data = self._fetch_ride_state(player_id, world, player_profile)
                data.update(ride_data)
            self._apply_player_update(player_id, player_profile, data)
        except RequestException as e:
            self._handle_request_error(e, player_id)
        except Exception:
            _LOGGER.exception(
                "Error updating Zwift player %s", player_id
            )

    def _fetch_player_profile(self, player_id):
        """Fetch and enrich the player profile with computed fields."""
        _profile = self._client.get_profile(player_id)
        player_profile = _profile.profile or {}
        _LOGGER.debug("Zwift profile data: %s", player_profile)

        player_profile["playerLevel"] = int(
            player_profile.get("achievementLevel", 0) / 100
        )
        player_profile["runLevel"] = int(
            player_profile.get("runAchievementLevel", 0) / 100
        )
        player_profile["cycleProgress"] = int(
            player_profile.get("achievementLevel", 0) % 100
        )
        player_profile["runProgress"] = int(
            player_profile.get("runAchievementLevel", 0) % 100
        )

        latest_activity = _profile.latest_activity
        latest_activity["world_name"] = ZWIFT_WORLDS.get(
            latest_activity.get("worldId")
        )
        player_profile["latest_activity"] = latest_activity
        player_profile["world_name"] = ZWIFT_WORLDS.get(
            player_profile.get("worldId")
        )
        return player_profile

    def _fetch_ride_state(self, player_id, world, player_profile):
        """Fetch live ride data for an online player."""
        player_state = world.player_status(player_id)
        _LOGGER.debug("Zwift player state data: %s", player_state.player_state)

        altitude = (float(player_state.altitude) - 9000) / 2
        distance = float(player_state.distance)
        prev_data = self.players[player_id].data
        gradient = prev_data.get("gradient", 0)

        latest_activity = player_profile.get("latest_activity", {})
        rideons = latest_activity.get("activityRideOnCount", 0)
        if rideons > 0 and rideons > prev_data.get("rideons", 0):
            self.hass.bus.fire(
                EVENT_ZWIFT_RIDE_ON,
                {"player_id": player_id, "rideons": rideons},
            )

        if prev_data.get("distance", 0) > 0:
            delta_distance = distance - prev_data.get("distance", 0)
            delta_altitude = altitude - prev_data.get("altitude", 0)
            if delta_distance > 0:
                gradient = delta_altitude / delta_distance

        return {
            "online": True,
            "heartrate": int(float(player_state.heartrate)),
            "cadence": int(float(player_state.cadence)),
            "power": int(float(player_state.power)),
            "speed": player_state.speed / 1000000.0,
            "altitude": altitude,
            "distance": distance,
            "gradient": gradient,
            "rideons": rideons,
        }

    def _apply_player_update(self, player_id, player_profile, data):
        """Apply fetched data to the player model."""
        player = self.players[player_id]
        player.player_profile = player_profile
        player.data = data
        new_device_name = f"Zwift {player.friendly_player_id}"
        old_device_name = player.last_device_name
        if old_device_name is not None and old_device_name != new_device_name:
            player._device_name_changed = True
        player._last_device_name = new_device_name

    def _handle_request_error(self, error, player_id):
        """Handle RequestException from the Zwift API."""
        error_str = str(error)
        if "401" in error_str:
            self._client = None
            _LOGGER.warning("Zwift credentials are wrong or expired")
        elif "404" in error_str:
            _LOGGER.warning("Upstream Zwift 404 - will try later")
        elif "429" in error_str:
            current_interval = self.online_update_interval
            new_interval = self.online_update_interval + timedelta(seconds=0.25)
            self.online_update_interval = new_interval
            _LOGGER.warning(
                "Upstream request throttling 429 - increasing interval from %ss to %ss",
                current_interval.total_seconds(),
                new_interval.total_seconds(),
            )
        else:
            _LOGGER.exception(
                "Zwift API error while updating player %s: %s",
                player_id, error,
            )
