# HAUKI Raspberry Pi 1A+ Implementation Design

**Date:** 2026-05-31 (revised 2026-10-30)
**Branch:** raspberry-pi
**Status:** Approved

## Overview

HAUKI runs on a Raspberry Pi 1A+ (CPython) with a Waveshare 2.13" V4 e-paper HAT. It
reads electricity spot prices from Home Assistant and shows the current price and the
cheapest 1h, 2h and 4h windows ahead.

## Goals

- Display electricity spot prices (from the Home Assistant ENTSO-E integration) on the
  Waveshare 2.13" V4 e-ink display on the Raspberry Pi 1A+ GPIO/SPI header
- Run as a systemd service that starts on boot and restarts on failure

## Non-Goals

- Async/event-driven scheduler (synchronous loop is sufficient)
- Unit tests

## Repository Structure

```text
.
├── src/
│   ├── main.py           # Entry point, outer error loop
│   ├── config.py         # Config loader
│   ├── eink.py           # Screen layouts, drawn with Pillow
│   ├── epd.py            # Low-level e-paper driver (spidev + lgpio)
│   ├── homeassistant.py  # HA REST client (requests)
│   ├── prices.py         # Price data, slot math, cheapest-window search
│   ├── scheduler.py      # Minute-aligned loop
│   ├── healthcheck.py    # HA + price data health checks
│   └── exceptions.py     # Typed error hierarchy
├── tools/
│   └── display_test.py   # Staged panel test, PNG preview without hardware
├── LICENSES/             # Third-party licenses
├── hauki.service         # systemd unit file
├── config.json.example   # Configuration template
├── requirements.txt      # Python dependencies
└── Makefile              # install, lint, deploy targets
```

## Platform Integration

### Display: eink.py and epd.py

`epd.py` drives the SSD1680 controller directly. SPI goes through `spidev` on SPI0
CE0, and the kernel drives chip select. RST, DC and BUSY go through `lgpio` on
`/dev/gpiochip0`. `RPi.GPIO` cannot be used: it rejects the Pi 1A+'s old-style revision
code. `lgpio` is imported only when the panel is opened, because it creates a
notification pipe in `$LG_WD` (or the working directory) on import.

The RAM layout follows Waveshare's Raspberry Pi driver for the HAT: data entry mode
`0x03`, rows of 16 bytes (122 px padded), and the landscape image rotated 90 degrees.
Updates use a full refresh (`0xF7`) every 10th time and a fast refresh (`0xC7`)
otherwise. The fast refresh needs the fast OTP waveform, which is loaded by writing a
fake 100 °C temperature after each full refresh. Measured: full 2.27 s, fast 1.75 s.

`eink.py` draws the screens (`show_price()`, `show_error()`, `show_status()`) with
Pillow and DejaVu Sans TTF, and passes the RAM buffer to an `epd` object. The PNG
preview in `tools/display_test.py` passes its own object, so layouts can be checked
on a workstation without hardware. The price layout is sized for prices up to
999.99 c/kWh.

The HAT plugs onto the 40-pin header. RST, DC and BUSY are configurable in the
`display` section of `config.json`, with defaults matching the HAT (BCM 17, 25, 24).

### Time

The OS owns the clock (network time) and the local time zone (`/etc/localtime`,
including DST), and ENTSO-E timestamps are UTC. So there is no time zone code or
config: `prices.py` and `scheduler.py` use `time.time()`,
`datetime.fromisoformat(...).timestamp()` and
`time.strftime('%H:%M', time.localtime(ts))` directly. The Pi's time zone must be set
correctly (see `README.md`).

### Networking

Networking is owned by the OS. HAUKI has no network management of its own.

## Boot Sequence

```text
systemd (after network-online.target)
  └─ python3 src/main.py
       ├─ construct Config, Display, HomeAssistant,
       │  Prices, HealthChecker, TaskScheduler  (once, before loop)
       └─ loop forever:
            scheduler.run()       ← does not return under normal operation
            on HaukiError → show error on display, wait until next minute, retry
            on Exception  → show error on display, wait until next minute, retry
```

Network drops and process crashes are recovered by `systemd Restart=on-failure`.
The outer loop in `main.py` only handles transient HA/price data failures.

## Scheduler

`scheduler.run()` wakes 1 s after every full minute (`sleep_until_next_minute()`).
On each pass it runs the health check, and redraws when the 15-minute slot has
changed. Slot boundaries fall on full minutes, so a new price shows within seconds
of its quarter starting, and slow passes do not drift. `run()` forgets the last shown
slot when it is entered, so after an error screen the price is redrawn as soon as the
checks pass again.

## Price Source (ENTSO-E)

Prices come from the `entsoe_prices` integration
([mteiste/entsoe-prices](https://github.com/mteiste/entsoe-prices)).
`sensor.electricity_price` has the current price in c/kWh (VAT included) as its state.
The price curve is in `raw_today` + `raw_tomorrow`, as 15-minute items
`{start, end, price_eur_mwh, price_ct_kwh}` with UTC ISO timestamps.

The parser concatenates both lists and uses `price_ct_kwh`. It ignores
`tomorrow_valid`, because ENTSO-E publishes the first slots of the next local day
with today's auction and every slot present is a final price. It stops at the first
gap so the slot index arithmetic stays valid.

### Metering interval

Cheapest windows depend on how the customer's meter reports consumption.
`prices.metering_interval` is 900 for quarter-hour metering (windows may start at any
slot) or 3600 for hourly metering (each whole local hour is billed at its average
price, so windows start on the hour). The window average is the mean of its slots in
both cases; only the allowed start times differ.

The large number on the price screen is the price billed for the current metering
period (`Prices.get_metering_price()`): the slot price with quarter-hour metering,
the hour's average with hourly metering. When the two intervals differ, the current
slot price is also shown small, top right under the slot time in the header.

## Configuration

```json
{
  "homeassistant": {
    "url": "http://homeassistant.local:8123",
    "token": "your-long-lived-access-token-here",
    "timeout": 10
  },
  "prices": {
    "entity_id": "sensor.electricity_price",
    "slot_duration": 900,
    "metering_interval": 900,
    "refresh_interval": 14400
  },
  "display": {
    "rst_pin": 17,
    "dc_pin": 25,
    "busy_pin": 24,
    "font_path": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
  }
}
```

`config.json` is git-ignored. `config.json.example` is the template.

## Error Handling

Typed `HaukiError` subclasses propagate from `scheduler.run()` to `main.py`, which
shows the error on the display and retries just after the next full minute.
Unrecognised exceptions follow the same path. Network and clock problems are handled
at the OS/systemd level.

The health check only fails when there is no price for the current slot. Day-ahead
prices are final once published, and HAUKI holds them up to a day ahead, so short
network outages (the Pi's Wi-Fi drops now and then) do not interrupt the display. A
refresh that fails is retried every minute. Only when the prices run out does the
error screen appear: "Could not reach HA" if HA is unreachable, otherwise "Could not
fetch prices" with the reason.

## systemd Service

`hauki.service` runs `/usr/bin/python3 src/main.py` under a dedicated `hauki` system
user, starts after `network-online.target`, and uses `Restart=on-failure` with a 10 s
delay. The code is installed to `/opt/hauki/src` (root-owned, read-only for the
service), and `config.json` to `/opt/hauki` (root:hauki, 0640). `RuntimeDirectory=hauki`
with `LG_WD=/run/hauki` gives lgpio its pipe directory, and
`PYTHONDONTWRITEBYTECODE=1` avoids bytecode writes. There is no venv on the Pi; all
dependencies are apt packages. `make deploy` (workstation) copies the tree to the Pi
and runs `make install` there.

## Dependencies

All from Raspbian apt packages:

```text
python3-pil       # Image rendering and TTF font loading
python3-requests  # HTTP client for Home Assistant API
python3-spidev    # SPI access
python3-lgpio     # GPIO access via /dev/gpiochip0
fonts-dejavu-core # Display font
```

## Makefile Targets

| Target | Purpose |
|--------|---------|
| `make prepare` | Workstation dev setup: venv with Ruff + Pillow, Node.js + markdownlint |
| `make lint` | Run Ruff and markdownlint (always exits 0; read the output) |
| `make test-ha` | Validate HA API connectivity |
| `make deploy` | Copy to the Pi and run `make install` there (workstation) |
| `make install` | Install files, enable and (re)start the service (on the Pi) |
| `make clean` | Remove venv and caches |
