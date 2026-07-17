"""Device triggers for Zwift integration."""

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, EVENT_ZWIFT_RIDE_ON

TRIGGER_TYPE_RIDE_ON = "ride_on"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In([TRIGGER_TYPE_RIDE_ON]),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict]:
    """Return a list of triggers for a device."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if device is None:
        return []

    # Only offer triggers for Zwift devices
    player_id = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            player_id = identifier[1]
            break

    if player_id is None:
        return []

    return [
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: TRIGGER_TYPE_RIDE_ON,
            "metadata": {},
        }
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(config[CONF_DEVICE_ID])

    player_id = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            player_id = int(identifier[1])
            break

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_ZWIFT_RIDE_ON,
            event_trigger.CONF_EVENT_DATA: {
                "player_id": player_id,
            },
        }
    )

    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
