Custom component repository for HACS for the Zwift sensor!

https://community.home-assistant.io/t/zwift-sensor-component-feedback-and-testers-needed/87512


===========

This adds the component to include Zwift sensors in your Home Assistant instance!

Installation
===

1. Install this from HACs
2. Add a configuration similar to the one below to your HA configuration. Players should be a list of "player_id" numbers that you wish to track. Your own `player_id` will be automatically included unless you specify the `include_self` directive in your sensor config and set it to `false`

```
sensor:
  - platform: zwift
    username: !secret my_zwift_username
    password: !secret my_zwift_password
    players:
      - !secret my_friends_zwift_player_id
```

3. Restart HomeAssistant
