Custom component repository for HACS for the Zwift sensor!

https://community.home-assistant.io/t/zwift-sensor-component-feedback-and-testers-needed/87512


===========

This adds the component to include Zwift sensors in your Home Assistant instance!

Installation
===

1. Install this from HACs
2. Add a configuration similar to the one below to your HA configuration.

```
sensor:
  - platform: zwift
    username: !secret my_zwift_username
    password: !secret my_zwift_password
    players:
      - !secret my_friends_zwift_player_id
```

3. Restart HomeAssistant

### Configuration Tips and Tricks

* Use your Zwift email address for `my_zwift_username` above.
* `players:` should be a list of "player_id" numbers that you wish to track. 
  * Your own `player_id` will be automatically included unless you specify the `include_self` directive in your sensor config and set it to `false`

Events
===

This integration will emit the following events:

## `zwift_ride_on`

When an online player recieves a "Ride on!" from another player, this event will be emitted with the following data:

```
player_id: <the tracked player id recieving the ride on>
rideons: <the total number of ride ons recieved on the current ride>
```

This information can also be accessed from the `latest_activity` attribute on the `zwift_online_<playerid>` sensor in a template sensor if necessary:

`{{ state_attr('sensor.zwift_online_<playerid>','latest_activity').activityRideOnCount }}`

Attributes
===

The `sensor.zwift_online_<playerid>` is populated with a very large mess of attributes that come from the profile data in the Zwift API as well as the latest activity data. Users are encouraged to explore this data and decide what to do with it, but some examples of useful information found in these attributes are below. This information can be used to create template sensors within HomeAssistant or used to trigger automations.

* Number of followers
* Number of ride ons recieved on last/current ride
* Distance/Wattage/Elevation/Length/Calories/Title/Start&End Date of the last/current activity
* Total all time statistics (watt hours, distance, elevation etc)
* Current FTP
