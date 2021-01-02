"""
Support for the Zwift API to create sensors.

example configuration:

```
sensor:
  - platform: zwift
    username: !secret my_zwift_username
    password: !secret my_zwift_password
    players:
      - !secret my_zwift_player_id
      - !secret my_friends_zwift_player_id
```

"""

import logging
import threading
import time

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['zwift-client==0.2.0']

import voluptuous as vol
from datetime import timedelta
from homeassistant.components.sensor import PLATFORM_SCHEMA
try:
    from homeassistant.components.binary_sensor import BinarySensorEntity
except ImportError:
    from homeassistant.components.binary_sensor import BinarySensorDevice as BinarySensorEntity
from homeassistant.const import CONF_NAME, CONF_USERNAME, CONF_PASSWORD, EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import dispatcher_send, \
    async_dispatcher_connect
from homeassistant.helpers.event import async_call_later

CONF_UPDATE_INTERVAL = 'update_interval'
CONF_PLAYERS = 'players'
CONF_INCLUDE_SELF = 'include_self'

DATA_ZWIFT = 'zwift'

DEFAULT_NAME = 'Zwift'

SIGNAL_ZWIFT_UPDATE = 'zwift_update_{player_id}'

EVENT_ZWIFT_RIDE_ON = 'zwift_ride_on'

ZWIFT_IGNORED_PROFILE_ATTRIBUTES = [
    'privateAttributes',
    'publicAttributes'
]

ZWIFT_WORLDS = {
    1: "Watopia",
    2: "Richmond",
    3: "London",
    4: "New York",
    5: "Innsbruck",
    6: "Bologna",
    7: "Yorkshire",
    8: "Crit City",
    10: "France",
    11: "Paris"
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PLAYERS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_INCLUDE_SELF, default=True): cv.boolean,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_UPDATE_INTERVAL, default=timedelta(seconds=15)): (
        vol.All(cv.time_period, cv.positive_timedelta)),
})

SENSOR_TYPES = {
    'online': {'name': 'Online', 'binary': True, 'device_class': 'connectivity', 'icon': 'mdi:radio-tower'},
    'hr': {'name': 'Heart Rate', 'unit': 'bpm',  'icon': 'mdi:heart-pulse'},
    'speed': {'name': 'Speed', 'unit': 'mph', 'unit_metric': 'kmh', 'icon': 'mdi:speedometer'},
    'cadence': {'name': 'Cadence', 'unit': 'rpm', 'icon': 'mdi:rotate-right'},
    'power': {'name': 'Power', 'unit': 'W', 'icon': 'mdi:flash'},
    'altitude': {'name': 'Altitude', 'unit': 'ft', 'unit_metric': 'm', 'icon': 'mdi:altimeter'},
    'distance': {'name': 'Distance', 'unit': 'miles', 'unit_metric': 'm', 'icon': 'mdi:arrow-expand-horizontal'},
    'gradient': {'name': 'Gradient', 'unit': '%', 'icon': 'mdi:image-filter-hdr'},
    'level': {'name': 'Level', 'icon': 'mdi:stairs'},
    'runlevel': {'name': 'Run Level', 'icon': 'mdi:run-fast'},
    'cycleprogress': {'name': 'Cycle Progress', 'unit': '%', 'icon': 'mdi:transfer-right'},
    'runprogress': {'name': 'Run Progress', 'unit': '%', 'icon': 'mdi:transfer-right'},
}

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Zwift sensor."""

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    players = config.get(CONF_PLAYERS)
    name = config.get(CONF_NAME)
    update_interval = config.get(CONF_UPDATE_INTERVAL)
    include_self = config.get(CONF_INCLUDE_SELF)


    zwift_data = ZwiftData(update_interval, username, password, players, hass)
    try:
        await zwift_data._connect()
    except:
        _LOGGER.exception("Could not create Zwift sensor named '{}'!".format(name))
        return

    if include_self:
        zwift_data.add_tracked_player(zwift_data._profile.get('id'))

    async def update_data(now):
        if zwift_data._client is None:
            await zwift_data._connect()
        await hass.async_add_executor_job(zwift_data.update)

        next_update = zwift_data.update_interval
        if zwift_data.any_players_online:
            next_update = zwift_data.online_update_interval

        async_call_later(
            hass,
            next_update.total_seconds(),
            update_data
        )

    await update_data(None)

    dev = []
    for player_id in zwift_data.players:
        for variable in SENSOR_TYPES:
            if SENSOR_TYPES[variable].get('binary'):
                dev.append(ZwiftBinarySensorDevice(name, zwift_data, zwift_data.players[player_id], variable))
            else:
                dev.append(ZwiftSensorDevice(name, zwift_data, zwift_data.players[player_id], variable))

    async_add_entities(dev, True)


class ZwiftSensorDevice(Entity):
    def __init__(self, name, zwift_data, player, sensor_type):
        """Initialize the sensor."""
        self._base_name = name
        self._zwift_data = zwift_data
        self._player = player
        self._type = sensor_type
        self._state = None
        self._attrs = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} {} ({})".format(self._base_name,SENSOR_TYPES[self._type].get('name'),self._player.player_id)

    @property
    def friendly_name(self):
        """Return the friendly name of the sensor."""
        return "{} {} ({})".format(self._base_name,SENSOR_TYPES[self._type].get('name'),self._player.friendly_player_id)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        if self._zwift_data.is_metric:
            return SENSOR_TYPES[self._type].get('unit_metric') or SENSOR_TYPES[self._type].get('unit')
        return SENSOR_TYPES[self._type].get('unit')

    @property
    def icon(self):
        return SENSOR_TYPES[self._type].get('icon')

    def update(self):
        """Get the latest data from the sensor."""
        self._state = getattr(self._player,self._type)
        if self._type == 'online':
            p = self._player.player_profile
            self._attrs.update({k: p[k] for k in p if k not in ZWIFT_IGNORED_PROFILE_ATTRIBUTES})

    async def async_added_to_hass(self):
        """Register update signal handler."""
        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        async_dispatcher_connect(self.hass, SIGNAL_ZWIFT_UPDATE.format(player_id=self._player.player_id), async_update_state)

class ZwiftBinarySensorDevice(ZwiftSensorDevice, BinarySensorEntity):
    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return SENSOR_TYPES[self._type].get('device_class')

class ZwiftPlayerData:
    def __init__(self, player_id):
        self._player_id = player_id
        self.data = {}
        self.player_profile = {}

    @property
    def player_id(self):
        return self._player_id

    @property
    def friendly_player_id(self):
        return self.player_profile.get('firstName') or self.player_id

    @property
    def online(self):
        return self.data.get('online',False)

    @property
    def hr(self):
        return self.data.get('heartrate',0.0)

    @property
    def speed(self):
        return self.data.get('speed',0.0)

    @property
    def cadence(self):
        return self.data.get('cadence',0.0)

    @property
    def power(self):
        return self.data.get('power',0.0)

    @property
    def altitude(self):
        return self.data.get('altitude',0.0)

    @property
    def distance(self):
        return self.data.get('distance',0.0)

    @property
    def gradient(self):
        return self.data.get('gradient',0.0)

    @property
    def level(self):
        return self.player_profile.get('playerLevel',None)

    @property
    def runlevel(self):
        return self.player_profile.get('runLevel',None)

    @property
    def cycleprogress(self):
        return self.player_profile.get('cycleProgress',None)

    @property
    def runprogress(self):
        return self.player_profile.get('runProgress',None)

class ZwiftData:
    """Representation of a Zwift client data collection object."""
    def __init__(self, update_interval, username, password, players, hass):
        self._client = None
        self.username = username
        self.password = password
        self.hass = hass
        self.players = {}
        self._profile = None
        self.update_interval = update_interval
        self.online_update_interval = timedelta(seconds=1)
        if players:
            for player_id in players:
                self.add_tracked_player(player_id)

    def add_tracked_player(self, player_id):
        if player_id:
            self.players[player_id] = ZwiftPlayerData(player_id)

    @property
    def any_players_online(self):
        return sum([p.online for p in self.players.values()]) > 0

    async def check_zwift_auth(self, client):
        token = await self.hass.async_add_executor_job(client.auth_token.fetch_token_data)
        if 'error' in token:
            raise Exception("Zwift authorization failed: {}".format(token))
        return True

    @property
    def is_metric(self):
        if self._profile:
            return self._profile.get('useMetric',False)
        return False

    async def _connect(self):
        from zwift import Client as ZwiftClient
        client = ZwiftClient(self.username,self.password)
        if await self.check_zwift_auth(client):
            self._client = client
            self._profile = await self.hass.async_add_executor_job(self._get_self_profile)
            return self._client

    def _get_self_profile(self):
        return self._client.get_profile().profile

    def update(self):
        from zwift.error import RequestException
        if self._client:
            world = self._client.get_world(1)
            for player_id in self.players:
                data = {}
                online_player = {}
                try:

                    _profile = self._client.get_profile(player_id)
                    player_profile = _profile.profile or {}
                    total_experience = int(player_profile.get('totalExperiencePoints'))
                    player_profile['playerLevel'] = int(player_profile.get('achievementLevel',0) / 100) 
                    player_profile['runLevel'] = int(player_profile.get('runAchievementLevel',0) / 100)
                    player_profile['cycleProgress'] = int(player_profile.get('achievementLevel',0) % 100)
                    player_profile['runProgress'] = int(player_profile.get('runAchievementLevel',0) % 100)
                    latest_activity = _profile.latest_activity
                    latest_activity['world_name'] = ZWIFT_WORLDS.get(latest_activity.get('worldId'))
                    player_profile['latest_activity'] = latest_activity

                    data['total_experience'] = total_experience
                    data['level'] = player_profile['playerLevel']
                    player_profile['world_name'] = ZWIFT_WORLDS.get(player_profile.get('worldId'))

                    if player_profile.get('riding'):
                        player_state = world.player_status(player_id)
                        altitude = (float(player_state.altitude) - 9000) / 2 # [TODO] is this correct regardless of metric/imperial? Correct regardless of world?
                        distance = float(player_state.distance)
                        gradient = self.players[player_id].data.get('gradient')
                        rideons = latest_activity.get('activityRideOnCount',0)
                        if rideons > 0 and rideons > self.players[player_id].data.get('rideons',0):
                            self.hass.bus.fire(EVENT_ZWIFT_RIDE_ON, {
                                'player_id': player_id,
                                'rideons': rideons
                            })
                        if self.players[player_id].data.get('distance',0) > 0:
                            delta_distance = distance - self.players[player_id].data.get('distance',0)
                            delta_altitude = altitude - self.players[player_id].data.get('altitude',0)
                            if delta_distance > 0:
                                gradient = delta_altitude / delta_distance
                        data.update({
                            'online': True,
                            'heartrate': int(float(player_state.heartrate)),
                            'cadence': int(float(player_state.cadence)),
                            'power': int(float(player_state.power)),
                            'speed': player_state.speed / 1000000.0,
                            'altitude': altitude,
                            'distance': distance,
                            'gradient': gradient,
                            'rideons': rideons
                        })
                    online_player.update(player_profile)
                    self.players[player_id].player_profile = online_player
                except RequestException as e:
                    if '401' in str(e):
                        self._client = None
                        _LOGGER.warning('Zwift credentials are wrong or expired')
                    elif '404' in str(e):
                        _LOGGER.warning('Upstream Zwift 404 - will try later')
                    else:
                        _LOGGER.exception('something went wrong in Zwift python library - {} while updating zwift sensor for player {}'.format(str(e), player_id))
                except Exception as e:
                    _LOGGER.exception('something went major wrong while updating zwift sensor for player {}'.format(player_id))
                self.players[player_id].data = data
                _LOGGER.debug("dispatching zwift data update for player {}".format(player_id))
                dispatcher_send(self.hass, SIGNAL_ZWIFT_UPDATE.format(player_id=player_id))

