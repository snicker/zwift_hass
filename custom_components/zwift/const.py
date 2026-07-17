"""Constants for the Zwift integration."""

import logging

_LOGGER = logging.getLogger('zwift')

DOMAIN = "zwift"

CONF_PLAYERS = "players"
CONF_INCLUDE_SELF = "include_self"

DEFAULT_NAME = "Zwift"

EVENT_ZWIFT_RIDE_ON = "zwift_ride_on"

ZWIFT_IGNORED_PROFILE_ATTRIBUTES = [
    "privateAttributes",
    "publicAttributes",
    "connectedToStrava",
    "connectedToTrainingPeaks",
    "connectedToTodaysPlan",
    "connectedToUnderArmour",
    "connectedToWithings",
    "connectedToFitbit",
    "connectedToGarmin",
    "connectedToRuntastic",
    "mixpanelDistinctId",
    "bigCommerceId",
    "avantlinkId",
    "userAgent",
    "launchedGameClient",
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
    9: "Makuri Islands",
    10: "France",
    11: "Paris",
}

SENSOR_TYPES = {
    "online": {"name": "Online", "entity_class": "ZwiftOnlineSensorEntity", "device_class": "connectivity", "icon": "mdi:radio-tower"},
    "hr": {"name": "Heart Rate", "unit": "bpm", "icon": "mdi:heart-pulse"},
    "speed": {"name": "Speed", "unit": "km/h", "device_class": "speed", "suggested_unit_imperial": "mph", "icon": "mdi:speedometer"},
    "cadence": {"name": "Cadence", "unit": "rpm", "icon": "mdi:rotate-right"},
    "power": {"name": "Power", "unit": "W", "device_class": "power", "icon": "mdi:flash"},
    "altitude": {"name": "Altitude", "unit": "cm", "device_class": "distance", "suggested_unit_metric": "m", "suggested_unit_imperial": "ft", "icon": "mdi:altimeter"},
    "distance": {"name": "Distance", "unit": "m", "device_class": "distance", "suggested_unit_metric": "km", "suggested_unit_imperial": "mi", "icon": "mdi:arrow-expand-horizontal"},
    "gradient": {"name": "Gradient", "unit": "%", "icon": "mdi:image-filter-hdr"},
    "level": {"name": "Level", "entity_category": "diagnostic", "icon": "mdi:stairs"},
    "runlevel": {"name": "Run Level", "entity_category": "diagnostic", "icon": "mdi:run-fast"},
    "cycleprogress": {"name": "Cycle Progress", "entity_category": "diagnostic", "unit": "%", "icon": "mdi:transfer-right"},
    "runprogress": {"name": "Run Progress", "entity_category": "diagnostic","unit": "%", "icon": "mdi:transfer-right"},
    "totaldistance": {"name": "Total Distance", "unit": "m", "entity_category": "diagnostic", "device_class": "distance", "suggested_unit_metric": "km", "suggested_unit_imperial": "mi", "icon": "mdi:map-marker-distance"},
    "totaldistanceclimbed": {"name": "Total Distance Climbed", "entity_category": "diagnostic",  "unit": "m", "device_class": "distance", "suggested_unit_metric": "km", "suggested_unit_imperial": "ft", "icon": "mdi:elevation-rise"},
    "totaltimeinminutes": {"name": "Total Time", "unit": "min", "device_class": "duration", "entity_category": "diagnostic", "suggested_unit_metric": "d", "suggested_unit_imperial": "d", "icon": "mdi:clock-outline"},
    "totalgold": {"name": "Drops", "entity_category": "diagnostic", "icon": "mdi:water"},
    "streakscurrentlength": {"name": "Current Streak", "unit": "w", "entity_category": "diagnostic", "icon": "mdi:fire"},
    "streaksmaxlength": {"name": "Max Streak", "unit": "w", "entity_category": "diagnostic", "icon": "mdi:trophy"},
    "racingscore": {"name": "Racing Score", "entity_category": "diagnostic", "icon": "mdi:podium"},
    "racingcategory": {"name": "Racing Category", "entity_category": "diagnostic", "icon": "mdi:format-list-numbered"},
    "ftp": {"name": "FTP", "unit": "W", "device_class": "power", "entity_category": "diagnostic", "icon": "mdi:flash"},
    "weight": {"name": "Weight", "unit": "g", "device_class": "weight", "entity_category": "diagnostic", "suggested_unit_metric": "kg", "suggested_unit_imperial": "lb", "icon": "mdi:weight"},
    "height": {"name": "Height", "unit": "mm", "device_class": "distance", "entity_category": "diagnostic", "suggested_unit_metric": "m", "suggested_unit_imperial": "ft", "icon": "mdi:human-male-height"},
    "dob": {"name": "Date of Birth", "device_class": "date", "entity_category": "diagnostic", "self_only": True, "icon": "mdi:cake-variant"},
    "age": {"name": "Age", "entity_category": "diagnostic", "icon": "mdi:calendar-account"},
    "createdon": {"name": "Account Created", "device_class": "timestamp", "entity_category": "diagnostic", "icon": "mdi:calendar-plus"},
    "powerzone": {"name": "Power Zone", "icon": "mdi:gauge"},
    "powerzonename": {"name": "Power Zone Name", "icon": "mdi:gauge", "device_class": "enum", "entity_class": "ZwiftPowerZoneSensorEntity"},
    "sport": {"name": "Sport", "icon": "mdi:bike", "device_class": "enum", "entity_class": "ZwiftSportSensorEntity"},
}

SPORT_OPTIONS = [
    "cycling",
    "running",
]

POWER_ZONE_OPTIONS = [
    "active_recovery",
    "endurance",
    "tempo",
    "threshold",
    "vo2max",
    "anaerobic",
    "neuromuscular",
]

POWER_ZONES = (
    (0.55, 1, "active_recovery", "#808080"),
    (0.75, 2, "endurance", "#3399FF"),
    (0.90, 3, "tempo", "#00CC00"),
    (1.05, 4, "threshold", "#FFD700"),
    (1.20, 5, "vo2max", "#FF8C00"),
    (1.50, 6, "anaerobic", "#FF0000"),
)
POWER_ZONE_NEUROMUSCULAR = (7, "neuromuscular", "#800080")
