# HAUKI Source Code

Architecture overview for the `src/` directory — intended for developers adapting or extending the codebase.

## File Overview

| File | Role |
|------|------|
| `boot.py` | MicroPython boot hook — safe mode gate |
| `main.py` | Entry point — wires components together, outer retry loop |
| `config.py` | Loads `config.json` from the filesystem |
| `exceptions.py` | Typed error hierarchy |
| `wifi.py` | WiFi connection and NTP sync |
| `homeassistant.py` | Home Assistant REST API client |
| `nordpool.py` | Nord Pool price data via HA — slot math, window search |
| `timezone.py` | UTC↔local time, DST transitions, ISO 8601 parsing |
| `scheduler.py` | Interval-based task loop |
| `healthcheck.py` | Per-iteration system health gate |
| `eink.py` | E-paper display driver and layout |

## Boot Sequence

```text
boot.py
  └─ checks GP15 (pull-up). If grounded → print safe mode, exit (skip main.py)

main.py
  ├─ construct Config, LocalTimezone, EPD_Landscape, PriceDisplay, WiFi,
  │  HomeAssistant, NordPool, HealthChecker, TaskScheduler  (once, before loop)
  ├─ show "Starting..."
  └─ loop forever:
       connect_wifi()
       sync_clock()          ← must succeed before scheduler; raises RtcSyncError if not
       scheduler.run()       ← does not return under normal operation
       on HaukiError → show error display, sleep 60s, retry outer loop
       on Exception  → show error display, sleep 60s, retry outer loop
```

All objects are constructed **once** before the loop to avoid reallocation on each retry. The outer loop only re-enters `scheduler.run()` after a full WiFi reconnect and NTP sync.

## Component Interactions

```text
main.py
  ├── Config ──────────────────────────────────────────────┐
  │                                                         ↓ (settings)
  ├── WiFi ────────────────────────────────── HomeAssistant
  │     │ NTP sync                                  │ REST
  │     │                                           ↓
  ├── LocalTimezone ← ── ── ── ── ──── NordPool (slot math, price fetch)
  │                                         │
  ├── HealthChecker ←── WiFi, HA, NordPool  │
  │                                         │
  └── TaskScheduler ←── Display, Health, NordPool, WiFi, Clock
```

## Time and Slots

All timestamps are **MicroPython epoch** (2000-01-01 00:00:00 UTC), not Unix epoch. This is transparent inside the codebase since it never converts to real Unix time, but matters if integrating external systems.

The clock is set via NTP on startup and re-synced every 6 hours. If the RTC has not been synced (fresh boot, NTP failure), `time.time()` returns a value near the MicroPython epoch (2021-01-01 default). `NordPool._get_slot()` will return slot 0 in this case, which is interpreted as "no valid data yet".

**Price slots** divide the day into fixed-duration windows (default 15 minutes / 900 seconds, configurable). The `prices` list always has a `None` sentinel at index 0. Slot index arithmetic:

- `slot_index = (timestamp - prices_start_utc) / slot_duration`
- Stored at `prices[slot_index + 1]` due to the sentinel
- `slot == 0` means either no data fetched yet, or current time is outside the known price range

`find_cheapest_window()` searches from `current_slot + 1` onwards — the current slot is already in progress and cannot be acted upon.

## Health-Check Loop

`HealthChecker.check()` is called at the start of every scheduler iteration. It checks in order:

1. WiFi connected
2. Home Assistant reachable (HTTP GET to `/api/`)
3. Nord Pool price available for the current slot (triggers a lazy refresh)

The first failure raises the appropriate `HaukiError` subclass, which propagates out of `scheduler.run()` and is caught in the outer loop of `main.py`. This is the reconnection mechanism — there is no separate WiFi-drop handler.

## Error Handling

All domain errors are typed subclasses of `HaukiError(RuntimeError)`. Each carries a short `message` (shown large on display) and optional `detail` string. Unrecognised exceptions are caught separately in `main.py` and shown as "Unexpected error".

Errors are never swallowed silently — `sys.print_exception()` is used so the full traceback appears on the serial console even when the display shows a short message.

## Display Assumptions

`EPD_Landscape` wraps the Waveshare 2.13" V4 in **landscape orientation** (250×122). The hardware is physically portrait (122×250), so `_send_display_buffer()` transposes the MONO_VLSB framebuffer before transmission.

`PriceDisplay` uses five fixed font sizes (12, 14, 32, 48 pt) laid out at hardcoded pixel coordinates. If the font or display size changes, all `set_textpos` calls in `show_price()`, `show_error()`, and `show_status()` need to be updated manually.

The display alternates between fast refresh (~1 s) and periodic full refresh (~2 s). `REFRESH_THRESHOLD = 10` controls how many fast refreshes occur between full refreshes — tuned empirically for this display model before ghosting becomes visible.

## DST Rules

`LocalTimezone` supports both northern hemisphere (DST start month < end month, simple range check) and southern hemisphere (DST spans year boundary, wrapping check). The active-year transitions are recalculated on the first call where the year differs from the cached one.

`format_local_time()` applies the correct offset at point of formatting. Slot timestamps stored in `NordPool` are always UTC; local time is only produced when building the display string.

## Key Assumptions to Keep in Mind

- **Single data source**: All price data comes from one Home Assistant `sensor.*` entity. The entity must expose `today`, `tomorrow`, `tomorrow_valid`, `raw_today`, and `unit_of_measurement` attributes (standard Nord Pool integration format).
- **15-minute slots by default**: `slot_duration` in config must match the resolution the Nord Pool integration actually delivers. Changing it without matching HA data will silently produce wrong slot indices.
- **No persistence**: Nothing is written to flash during normal operation. On reboot all state is lost and the outer loop restarts from WiFi connect.
- **No async / no threading**: Entirely synchronous and single-threaded. The scheduler sleeps with `time.sleep()`.
- **safe mode via GPIO**: Grounding GP15 at boot skips `main.py` entirely, giving REPL access for recovery without uploading new firmware.
- **config.json on the Pico**: `Config` opens `config.json` relative to the working directory. The file must be uploaded to the root of the Pico filesystem.
