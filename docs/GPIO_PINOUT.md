# GPIO Pinout

This table tracks the physical Raspberry Pi header pins used by Raspi Hotspot. Code and dashboard configuration use BCM GPIO numbers.

The app creates GPIO17, GPIO27, and GPIO23 automatically on startup. The dashboard labels are `Building Door`, `Apartment Door`, and `Door Sensor`.

## Current Pin Assignments

| Physical pin | BCM GPIO | Function | Notes |
|---:|---:|---|---|
| 2 | 5V | Relay power | Relay board VCC |
| 6 | GND | Relay ground | Relay board GND |
| 11 | 17 | Building / street door relay | Output to relay IN1 |
| 13 | 27 | Apartment door relay | Output to relay IN2 |
| 14 | GND | Reed sensor ground | Ground side |
| 16 | 23 | Reed sensor signal | Input with internal pull-up |

## Legend

- Physical pin: board/header pin number
- BCM GPIO: GPIO number used in code, gpiozero, and dashboard pin configuration
- Relay outputs use active-low relay board behavior in `gpio_service.py`

## Reed Sensor Notes

- The reed switch uses GPIO23 (physical pin 16) with internal pull-up enabled in software.
- The other side of the reed switch connects to GND (physical pin 14).
- Circuit closed to GND / magnet present is logged as `closed`; circuit open / magnet away is logged as `open`.

See [HARDWARE.md](HARDWARE.md) for wiring and test steps.
