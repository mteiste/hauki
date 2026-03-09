# boot.py -- run on boot-up
# This file is executed on every boot (including wake-boot from deep sleep)
# Keep this file minimal to avoid boot failures that make REPL inaccessible

import sys

import machine

safe_pin = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)

if safe_pin.value() == 0:
    print("SAFE MODE - SKIPPING MAIN.PY")
    sys.exit()
