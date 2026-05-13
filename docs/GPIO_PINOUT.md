# Raspberry Pi GPIO Pinout (Raspi Hotspot)

This document tracks the GPIO pin assignments for the Raspi Hotspot project. Update this file whenever hardware connections change or new sensors/actuators are added.

## Current Pin Assignments

| Pin # | GPIO # | Function                | Usage/Notes                |
|-------|--------|-------------------------|----------------------------|
| 2     | 5V     | Power                   | Relay board VCC            |
| 6     | GND    | Ground                  | Relay board GND            |
| 11    | 17     | Relay 1 (street door)   | Output to relay IN1        |
| 13    | 27     | Relay 2 (apartment door)| Output to relay IN2        |

## Planned/Available

| Pin # | GPIO # | Function                | Usage/Notes                |
|-------|--------|-------------------------|----------------------------|
| 14    | GND    | Reed sensor (door)      | Ground side                |
| 16    | 23     | Reed sensor (door)      | Input, pull-up, open/close |

## Legend
- Pin #: Physical pin number on Pi header (BOARD numbering)
- GPIO #: BCM numbering (as used in code)
- Function: Device or purpose
- Usage/Notes: Details or wiring notes

## To Add: Reed Sensor
- Use a free GPIO pin (e.g., GPIO22, physical pin 15) for the reed switch.
- Connect one side of the reed switch to the chosen GPIO pin, the other to GND.
- Enable internal pull-up in software.

Update this file with the actual pin chosen for the reed sensor after wiring.
