Custom component repository for HACS for the Zwift sensor!

https://community.home-assistant.io/t/zwift-sensor-component-feedback-and-testers-needed/87512


===

This adds the component to include Zwift sensors in your Home Assistant instance!

Installation via HACS
===

[![Open your Home Assistant instance and adding repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=snicker&repository=zwift_hass&category=integration)

1. Install this from HACS 
2. Restart Home Assistant

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=zwift_hass)

3. Go to **Settings → Devices & Services → Add Integration** and search for **Zwift Sensor**
4. Enter your Zwift credentials
5. The integration will fetch your Zwift followees and present them as a list — select the players you want to track
6. You can also add players by entering a custom player ID in the selection field
7. Your own player will be included automatically unless you uncheck "Include own profile"

Devices & Entities
===

Each tracked player is represented as a **device** in Home Assistant, named using the player's full name (first and last) from their Zwift profile. The device page includes:

* A link to the player's Zwift profile at `zwift.com/athlete/<player_id>`
* A **Profile Picture** image entity

The following **sensor entities** are created per player:

| Entity | Type | Description |
|--------|------|-------------|
| Online | Binary sensor | Whether the player is currently riding |
| Heart Rate | Sensor | Current heart rate (bpm) |
| Speed | Sensor | Current speed (mph / kmh) |
| Cadence | Sensor | Current cadence (rpm) |
| Power | Sensor | Current power (W) |
| Altitude | Sensor | Current altitude (ft / cm) |
| Distance | Sensor | Distance ridden (miles / m) |
| Gradient | Sensor | Current gradient (%) |
| Level | Sensor | Cycling level |
| Run Level | Sensor | Running level |
| Cycle Progress | Sensor | Progress to next cycling level (%) |
| Run Progress | Sensor | Progress to next running level (%) |
| Total Distance | Sensor | Total all-time distance (m) |
| Total Distance Climbed | Sensor | Total all-time elevation climbed (ft / m) |
| Total Time In Minutes | Sensor | Total all-time ride time (min) |
| Drops | Sensor | Total in-game currency (Drops) |
| Current Streak | Sensor | Current activity streak (days) |
| Max Streak | Sensor | Longest activity streak (days) |
| Racing Score | Sensor | Competition racing score |
| Racing Category | Sensor | Racing category (uses women's category when applicable) |
| FTP | Sensor | Functional Threshold Power (W) |

Managing Players
===

To add or remove tracked players after initial setup:

1. Go to **Settings → Devices & Services → Zwift Sensor**
2. Click **Configure**
3. Your current followees will be fetched and shown as a selectable list — check or uncheck players as needed
4. You can also add custom player IDs that are not in your followees list
5. Click Submit

The integration will reload automatically and devices for removed players will be cleaned up.

Events
===

This integration will emit the following events:

## `zwift_ride_on`

When an online player receives a "Ride On!" from another player, this event will be emitted with the following data:

```
player_id: <the tracked player id receiving the ride on>
rideons: <the total number of ride ons received on the current ride>
```

### Device Trigger

The `zwift_ride_on` event is also available as a **device trigger** for automations. When creating an automation, select a Zwift player device and choose the **"Ride On received"** trigger.

### Template Access

This information can also be accessed from the `latest_activity` attribute on the Online sensor in a template:

`{{ state_attr('sensor.zwift_online_<playerid>','latest_activity').activityRideOnCount }}`

Attributes
===

The Online sensor is populated with attributes from the Zwift API profile data and latest activity data. Users are encouraged to explore this data and decide what to do with it. Some examples of useful information:

* Number of followers
* Number of ride ons received on last/current ride
* Distance/Wattage/Elevation/Length/Calories/Title/Start&End Date of the last/current activity
* Total all time statistics (watt hours, distance, elevation etc)
* Current FTP

Upgrading from older versions
===

Previous versions of this integration required entering player IDs manually as a comma-separated string. The new version lets you select players from your Zwift followees list instead.

### YAML configuration

If you configured this integration via `configuration.yaml` in a previous version, **no changes are necessary** — both the original `sensor:` platform format and the newer `zwift:` format are imported automatically on upgrade:

```yaml
# Original format — imported automatically, no edits needed:
sensor:
  - platform: zwift
    username: !secret my_zwift_username
    password: !secret my_zwift_password
    players:
      - !secret my_friends_zwift_player_id

# Newer format — also imported automatically, no edits needed:
zwift:
  username: !secret my_zwift_username
  password: !secret my_zwift_password
  players:
    - !secret my_friends_zwift_player_id
```

Just upgrade and restart Home Assistant. Either format is automatically imported into a config entry under **Settings → Devices & Services**, and your existing entities keep their history (matched against their previous unique IDs). Home Assistant will also show a notice under **Settings → Repairs** once the import completes, letting you know the YAML block is no longer needed and can be safely removed at your convenience — leaving it in place is harmless, it just won't do anything further.

To manage tracked players going forward, click **Configure** on the integration to select from your followees list rather than editing YAML.

### Device naming change

Devices are now named using the player's **full name** (first + last) from their Zwift profile instead of just the first name. After upgrading, your device names will update automatically on the next data refresh. This may affect automations or dashboard cards that reference device names — entity IDs are unchanged.
