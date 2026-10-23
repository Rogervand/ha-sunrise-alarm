# Sunrise Alarm Clock for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/Rogervand/ha-sunrise-alarm/actions/workflows/validate.yml/badge.svg)](https://github.com/Rogervand/ha-sunrise-alarm/actions/workflows/validate.yml)

A wake-up alarm that fades your lights in like a sunrise, then starts music on a speaker (Sonos or any media player) with a gentle volume ramp. Each alarm is a device with its own entities, so it works from the included dashboard card, the device page, automations, voice assistants, or Apple Home via HomeKit Bridge.

![Sunrise Alarm card](docs/card.png)

## Features

- **Light sunrise** – lights start at 1% warm white N minutes before the alarm and reach 100% cooler white at ring time. Color temperature is clamped to what each bulb supports; bulbs without color temperature just fade brightness.
- **Music with volume ramp** – plays a media content ID, selects a source/Sonos favorite, or resumes playback, then ramps from a start to an end volume.
- **Repeat days or one-shot** – pick weekdays, or none for a one-time alarm that switches itself off afterwards.
- **Snooze, dismiss, auto-dismiss** – snooze pauses music and rings again; dismiss stops it. Dismissing during the light fade skips just that day.
- **Dashboard card included** – installed automatically with the integration; no separate resource to add.
- **Events** for your own automations: `sunrise_alarm_pre_wake`, `sunrise_alarm_ringing`, `sunrise_alarm_snoozed`, `sunrise_alarm_dismissed`.
- DST-safe scheduling; alarm time, days and on/off survive restarts.

## Installation

### HACS

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Rogervand&repository=ha-sunrise-alarm&category=integration)

1. In HACS, search for **Sunrise Alarm Clock** and download it (or add this repository as a custom repository, category *Integration*).
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → Sunrise Alarm Clock.**

### Manual

Copy `custom_components/sunrise_alarm` into your `config/custom_components/` folder and restart.

## Setup

Each alarm is one integration entry. The setup form asks what should wake you:

| Option | Default | Notes |
|---|---|---|
| Speaker | – | Any `media_player`. Optional if you only use lights. |
| Source / favorite | – | e.g. a Sonos favorite name exactly as it appears in the player's source list. |
| Media content ID | – | Takes priority over Source. For Sonos favorites use type *Sonos favorite* and an ID like `FV:2/12` (find it in **Developer tools → Actions → media_player.browse_media**). |
| Starting / final volume | 5% / 30% | |
| Volume ramp | 5 min | 0 jumps straight to final volume. |
| Lights | – | One or more lights. |
| Light fade-in | 15 min | How long before the alarm the sunrise starts. |
| Start / end color temp | 2200 K / 4000 K | |
| Snooze length | 9 min | |
| Auto-dismiss after | 30 min | 0 = never. |

Change these later with **Configure** on the integration entry. Set the **time and days** on the card or the device page.

## Dashboard card

The card is registered automatically. Add it from the card picker (search *Sunrise Alarm*) or in YAML:

```yaml
type: custom:sunrise-alarm-card
entity: sensor.bedroom_alarm_next_alarm
# name: Bedroom          # optional
# show_days: true        # weekday buttons
# show_details: true     # "Lights from N min before"
```

Tap the time to change it, tap day letters to toggle repeat days. While ringing it shows **Snooze** and **Dismiss**; during the light fade it shows **Skip today**.

## Entities (per alarm)

| Entity | Purpose |
|---|---|
| `time.<alarm>_alarm_time` | Alarm time |
| `switch.<alarm>_alarm` | Alarm on/off |
| `switch.<alarm>_monday` … `_sunday` | Repeat days (config entities) |
| `sensor.<alarm>_next_alarm` | Next ring time (timestamp) |
| `sensor.<alarm>_status` | `idle`, `pre_wake`, `ringing`, `snoozed` |
| `button.<alarm>_snooze` / `_dismiss` | Available only while ringing / active |
| `button.<alarm>_test_alarm` | Ring now |

## Actions

All take `config_entry_id` (pick the alarm in the UI).

| Action | Fields |
|---|---|
| `sunrise_alarm.set_time` | `time` |
| `sunrise_alarm.set_days` | `days`: list of `mon`…`sun` (empty = one-shot) |
| `sunrise_alarm.snooze` | |
| `sunrise_alarm.dismiss` | |
| `sunrise_alarm.trigger` | Ring now |

## Automation examples

Skip the alarm when nobody is home:

```yaml
automation:
  - alias: Alarm off when away
    triggers:
      - trigger: state
        entity_id: zone.home
        to: "0"
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.bedroom_alarm_alarm
```

Open the blinds when the alarm rings:

```yaml
automation:
  - alias: Blinds up on alarm
    triggers:
      - trigger: event
        event_type: sunrise_alarm_ringing
        event_data:
          name: Bedroom alarm
    actions:
      - action: cover.open_cover
        target:
          entity_id: cover.bedroom_blinds
```

Event data contains `config_entry_id`, `name` and `alarm_time` (plus `snooze_until` for snoozes).

## Notes

- If Home Assistant restarts while an alarm is ringing, the alarm resets to idle and arms the next occurrence.
- A speaker or light that fails doesn't stop the rest of the wake sequence; failures are logged as warnings.
- Brand icons ship in `custom_components/sunrise_alarm/brand/` (shown on Home Assistant 2026.3+).

## Development

```bash
pip install -r requirements_test.txt
python -m pytest
```
