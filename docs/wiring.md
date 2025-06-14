# Dock Wiring Guide

This document explains how to connect a 30‑pin iPod dock connector to a Raspberry Pi for syncing and playback control.

## Pin summary

```
Audio Out      L: pin 4   R: pin 3
Audio In       L: pin 6   R: pin 5
Audio GND      pin 2
Composite out  pin 8
S‑Video Chroma pin 9
S‑Video Luma   pin 10
Serial GND     pin 11
Serial TX      pin 12
Serial RX      pin 13
USB +5V        pin 23
USB GND        pin 16
USB D+         pin 27
USB D‑         pin 25
Firewire TPA+  pin 24
Firewire TPA‑  pin 22
Firewire TPB+  pin 28
Firewire TPB‑  pin 26
Firewire 12V   pins 19,20
Firewire GND   pins 29,30
3.3V Accessory pin 18
Accessory det. pin 21
Extra GND      pins 1,15
Reserved       pins 14,17
Unknown        pin 7
```

## Connecting to the Pi

1. **USB data** – wire dock pin 27 to the Pi's USB D+ and pin 25 to USB D–. The easiest approach is to cut a USB cable and match the colours (green is D+, white is D–). Connect pin 23 to the Pi's 5 V supply and pin 16 to ground. This lets the Pi recognise the iPod as a normal USB device for file transfers.
2. **Serial control** – connect pin 12 (TX) and pin 13 (RX) to the Pi's UART pins (GPIO14 TX and GPIO15 RX). Place a ~6.8 kΩ resistor between pin 21 and ground so the iPod enables accessory mode on those serial pins.
3. **Audio out** – pins 4 and 3 provide left and right line out with pin 2 as ground. You can feed these into an external amplifier or powered speaker if you want the dock to play music aloud.
4. The remaining pins are optional. FireWire power is not used and can be left unconnected.

After wiring the dock you can plug the USB lines into the Pi and enable serial login on `/dev/serial0` for the playback controller. The web UI exposes play, pause and track skip commands which are sent over this serial connection.
