# HAUKI Raspberry Pi 1A+ Implementation Design

**Date:** 2026-05-31
**Branch:** raspberry-pi
**Status:** Approved

## Overview

Port HAUKI from Raspberry Pi Pico W (MicroPython) to Raspberry Pi 1A+ (CPython).
The domain logic is unchanged; only the four platform seams are replaced.
Both implementations coexist in the same repo as independent siblings under `pico/`
and `rpi/`.

## Goals

- Display electricity spot prices (from the Home Assistant ENTSO-E integration) on the Waveshare 2.13" V4 e-ink display
  driven by the Raspberry Pi 1A+ GPIO/SPI header
- Run as a systemd service that starts on boot and restarts on failure
- Reuse the Pico's domain logic (price slot math, HA client, scheduler, exceptions)
  without modification where possible

## Non-Goals

- Shared code between `pico/` and `rpi/`
- Async/event-driven scheduler (synchronous loop is sufficient)
- Unit tests (same stance as the Pico implementation)

## Repository Structure

```text
rpi/
├── src/
│   ├── main.py           # Entry point
│   ├── config.py         # Config loader
│   ├── eink.py           # luma.epd + Pillow display driver
│   ├── homeassistant.py  # HA REST client (requests)
│   ├── prices.py         # Price data + slot math (Pico nordpool.py, adapted to ENTSO-E)
│   ├── scheduler.py      # Interval loop
│   ├── healthcheck.py    # HA + price data health checks
│   └── exceptions.py     # Typed error hierarchy
├── hauki.service         # systemd unit file
├── config.json.example   # Configuration template
├── requirements.txt      # Python dependencies
└── Makefile              # install, lint, deploy targets
```

## Platform Seam Replacements

### eink.py — Complete rewrite

**Pico:** `machine.SPI` + `machine.Pin` + `framebuf.FrameBuffer` (MONO_VLSB) +
micropython-font-to-py compiled fonts + custom `Writer` + manual buffer transpose.

**RPi:** `luma.epd.device.ssd1680` (same display controller chip, Waveshare 2.13" V4)
+ `PIL.Image` / `PIL.ImageDraw` + `PIL.ImageFont.truetype` (system TTF directly).
luma.epd owns the SPI communication and orientation; no manual buffer transformation
needed.

GPIO pins (RST, DC, CS, BUSY) must be rewired from the Pico header to the RPi 40-pin
header; the Pico pin numbers (12, 8, 9, 13) do not carry over. Pin assignments are
configurable in `config.json` under a `display` section. The defaults in
`config.json.example` match Waveshare's conventional RPi wiring (BCM 17, 25, 8, 24)
and should be adjusted to match actual wiring.

`PriceDisplay` keeps its existing public interface — `show_price()`, `show_error()`,
`show_status()` — so `scheduler.py` and `main.py` require no changes for the display.

### homeassistant.py — Dependency swap

Replace `mrequests.get()` with `requests.get()`. Response parsing and error handling
are identical.

### timezone.py — Deleted

*Revised 2026-10-30.* The OS owns the clock (network time) and the local time zone
(`/etc/localtime`, including DST), and ENTSO-E timestamps are UTC. So no time zone code
or config is needed: `prices.py` and `scheduler.py` use `time.time()`,
`datetime.fromisoformat(...).timestamp()` and
`time.strftime('%H:%M', time.localtime(ts))` directly. The Pi's time zone must be set
correctly (see `rpi/README.md`).

### wifi.py — Deleted

Networking is owned by the OS (NetworkManager / dhcpcd). No Python WiFi management.

## Boot Sequence

```text
systemd (after network-online.target)
  └─ python3 src/main.py
       ├─ construct Config, Display, HomeAssistant,
       │  Prices, HealthChecker, TaskScheduler  (once, before loop)
       └─ loop forever:
            scheduler.run()       ← does not return under normal operation
            on HaukiError → show error on display, sleep 60 s, retry
            on Exception  → show error on display, sleep 60 s, retry
```

WiFi drops and process crashes are recovered by `systemd Restart=on-failure`.
The outer loop in `main.py` only handles transient HA/price data failures.

## Module Change Summary

| Module | Change |
|--------|--------|
| `eink.py` | Full rewrite (luma.epd + Pillow) |
| `homeassistant.py` | `mrequests` → `requests` |
| `timezone.py` | Deleted; the OS local time zone is used directly |
| `main.py` | Remove WiFi/NTP steps; simplify outer loop |
| `scheduler.py` | Remove `six_hour_task` (NTP sync) |
| `healthcheck.py` | Remove WiFi check |
| `config.py` | Remove WiFi section; add optional `display` GPIO section |
| `exceptions.py` | Remove `WiFiConnectionError`, `RtcSyncError` |
| `prices.py` | Pico `nordpool.py` renamed; parser reads the ENTSO-E sensor (see below) |
| `boot.py` | Deleted (Pico safe-mode mechanism, not applicable) |

## Price Source (ENTSO-E)

*Added 2026-10-30.* Home Assistant switched from the Nord Pool integration to
`entsoe_prices` ([mte/entsoe-prices](https://git.teiste.dedyn.io/mte/entsoe-prices)),
so `nordpool.py` was renamed `prices.py` (class `Prices`) and its parser rewritten.

`sensor.electricity_price` has the current price in c/kWh (VAT included) as its state.
Unlike Nord Pool it has no flat `today`/`tomorrow` lists; the curve is only in
`raw_today` + `raw_tomorrow`, as 15-minute items
`{start, end, price_eur_mwh, price_ct_kwh}` with UTC ISO timestamps.

The parser concatenates both lists and uses `price_ct_kwh`. It ignores
`tomorrow_valid`, because ENTSO-E publishes the first slots of the next local day
with today's auction and every slot present is a final price. It stops at the first
gap so the slot index arithmetic stays valid. The slot math and cheapest-window
search are unchanged.

## Configuration

`config.json` follows the same schema as the Pico with these changes:

1. The `wifi` section is removed.
2. The `timezone` section is removed (the OS time zone is used).
3. `nordpool` is renamed `prices` and points at the ENTSO-E sensor.
4. A `display` section is added for GPIO pin assignments (optional; defaults to
   Waveshare's standard RPi wiring):

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
    "refresh_interval": 14400
  },
  "display": {
    "rst_pin": 17,
    "dc_pin": 25,
    "cs_pin": 8,
    "busy_pin": 24
  }
}
```

`config.json` is git-ignored. `config.json.example` is the template.

## Error Handling

Typed `HaukiError` subclasses propagate from `scheduler.run()` to `main.py`,
which shows the error on the display and sleeps 60 s before retrying. Unrecognised
exceptions follow the same path. `WiFiConnectionError` and `RtcSyncError` are removed;
those failure modes are now handled at the OS/systemd level.

## systemd Service

`hauki.service` runs under a dedicated `hauki` system user, starts after
`network-online.target`, and uses `Restart=on-failure` with a short restart delay.
The working directory is the `rpi/` checkout; `config.json` lives alongside it.

## Dependencies

```text
luma.epd       # Waveshare e-ink display driver
pillow         # Image rendering and TTF font loading
requests       # HTTP client for Home Assistant API
RPi.GPIO       # GPIO access (pulled in transitively by luma.epd)
spidev         # SPI access (pulled in transitively by luma.epd)
```

## Makefile Targets

| Target | Purpose |
|--------|---------|
| `make prepare` | Create venv, install dependencies |
| `make lint` | Run Ruff on `src/` |
| `make test-ha` | Validate HA API connectivity |
| `make install` | Install and enable the systemd service |
| `make clean` | Remove venv and caches |
