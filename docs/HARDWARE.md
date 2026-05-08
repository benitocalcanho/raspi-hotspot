# Hardware Setup — Raspberry Pi 3

# Hardware Setup — Raspberry Pi 3
# Hardware Setup — Raspberry Pi 3

## Board Overview

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

## Example: LED on BCM17

```
Pi BCM17 (pin 11) ── [330Ω resistor] ── LED(+) ── LED(-) ── GND (pin 9)
```

Configure in Admin Dashboard → GPIO → Add Pin:
- BCM pin: `17`
- Label: `Status LED`
- Direction: `Output`

## Power

Use a **5V 2.5A** power supply. Underpowered supplies cause SD card corruption.

## WiFi Note

Pi 3 has **one WiFi chip** (Broadcom BCM43438). This project uses a virtual `uap0`
interface for the hotspot alongside `wlan0` for the client connection — both run
simultaneously thanks to the Broadcom driver's AP+STA support.

If you experience instability, plug in a **USB WiFi dongle** and configure
`hostapd` to use that interface instead, freeing `wlan0` for client-only use.
