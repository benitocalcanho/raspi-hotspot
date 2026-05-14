# Hardware Setup

This document covers the physical wiring used by Raspi Hotspot. The app uses BCM GPIO numbering in code and in the admin UI.

Use [GPIO_PINOUT.md](GPIO_PINOUT.md) for the compact pin table.

## Raspberry Pi Header

```
                    Raspberry Pi 3 Model B/B+
                    ┌──────────────────────────────────┐
    Power (5V 2.5A) │  [PWR]   [HDMI]  [USB x4]  [ETH] │
                    │                                    │
                    │  ┌──────────────────────────────┐ │
                    │  │  GPIO Header (40 pins)        │ │
                    │  └──────────────────────────────┘ │
                    │  [CSI]  [DSI]  [MicroSD]  [WiFi]  │
                    └──────────────────────────────────┘
```

## GPIO Pin Map (BCM numbering)

```
      3.3V  (1) ● ● (2)  5V
  SDA GPIO2 (3) ● ● (4)  5V
  SCL GPIO3 (5) ● ● (6)  GND
     GPIO4  (7) ● ● (8)  GPIO14 (TXD)
       GND  (9) ● ● (10) GPIO15 (RXD)
    GPIO17 (11) ● ● (12) GPIO18
    GPIO27 (13) ● ● (14) GND
    GPIO22 (15) ● ● (16) GPIO23
      3.3V (17) ● ● (18) GPIO24
    GPIO10 (19) ● ● (20) GND
     GPIO9 (21) ● ● (22) GPIO25
    GPIO11 (23) ● ● (24) GPIO8
       GND (25) ● ● (26) GPIO7
     GPIO0 (27) ● ● (28) GPIO1
     GPIO5 (29) ● ● (30) GND
     GPIO6 (31) ● ● (32) GPIO12
    GPIO13 (33) ● ● (34) GND
    GPIO19 (35) ● ● (36) GPIO16
    GPIO26 (37) ● ● (38) GPIO20
       GND (39) ● ● (40) GPIO21
```

## Relay Outputs

The app creates the default GPIO configuration automatically on startup:

| Label | BCM GPIO | Direction |
|---|---:|---|
| Building Door | 17 | Output |
| Apartment Door | 27 | Output |
| Door Sensor | 23 | Input |

End users only need to wire the Raspberry Pi according to this pinout.

The default relay outputs are:

| Door | Physical pin | BCM GPIO | Notes |
|---|---:|---:|---|
| Building / street door | 11 | 17 | Relay IN1 |
| Apartment door | 13 | 27 | Relay IN2 |
| Relay power | 2 | 5V | Relay board VCC |
| Relay ground | 6 | GND | Relay board GND |

The GPIO service treats the relay board as active-low. A door unlock action pulses the configured output for 5 seconds.

## Power

Use a **5V 2.5A** power supply. Underpowered supplies cause SD card corruption.

## Reed Sensor (Door Open/Closed)

The reed switch records whether the door is open or closed.

| Reed wire | Physical pin | BCM GPIO | Notes |
|---|---:|---:|---|
| Signal | 16 | 23 | Input with internal pull-up |
| Ground | 14 | GND | Ground side |

The service uses:

```python
gpiozero.Button(23, pull_up=True, bounce_time=0.2)
```

Current software convention:

| Electrical state | Logged door state |
|---|---|
| Circuit closed to GND / magnet present | `closed` |
| Circuit open / magnet away | `open` |

If your reed switch is mounted in the opposite orientation, set `REED_ACTIVE_STATE=open` in the Pi environment.

## Enable GPIO Runtime

On Raspberry Pi, start with the Pi overlay:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d
```

This overlay sets `ENABLE_GPIO=true`, uses the real `gpiozero` driver, maps `/dev/gpiomem`, and mounts host D-Bus for dashboard WiFi management.

Do not add `privileged: true` for this app's normal GPIO usage.

## Reed Sensor Test

1. Confirm the signal wire is on physical pin 16 / GPIO23.
2. Confirm the other wire is on physical pin 14 / GND.
3. Start the app with the Pi overlay.
4. Log in as admin.
5. Open Admin Dashboard -> Door Log.
6. Open and close the door and confirm the state changes.

Manual shell check inside the running container:

```bash
docker exec -it raspi-hotspot python
```

```python
from gpiozero import Button

sensor = Button(23, pull_up=True)
print("closed" if sensor.is_pressed else "open")
```

## WiFi Hardware Note

Pi 3 has one onboard WiFi chip. The optional hotspot script tries to use a virtual `uap0` AP interface alongside `wlan0`.

If hotspot mode is unstable, use a USB WiFi adapter with AP mode support. The main Docker deployment does not require hotspot mode.
