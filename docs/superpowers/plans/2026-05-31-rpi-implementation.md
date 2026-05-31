# HAUKI Raspberry Pi 1A+ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port HAUKI from Raspberry Pi Pico W (MicroPython) to Raspberry Pi 1A+ (CPython) by replacing the four platform seams while keeping all domain logic intact.

**Architecture:** All files live under `rpi/src/`. The application is a long-running Python process managed by systemd. Only `eink.py`, `homeassistant.py`, `timezone.py`, `main.py`, `scheduler.py`, `healthcheck.py`, and `config.py` change; `nordpool.py` and `exceptions.py` are copied from `pico/src/` with minimal changes.

**Tech Stack:** CPython 3.9+, luma.epd, Pillow, requests, systemd, Ruff

---

## File Map

| File | Action | Notes |
|------|--------|-------|
| `rpi/requirements.txt` | Create | luma.epd, Pillow, requests |
| `rpi/.ruff.toml` | Create | CPython target (py39) |
| `rpi/config.json.example` | Create | WiFi removed, display section added |
| `rpi/Makefile` | Create | prepare, lint, test-ha, install targets |
| `rpi/hauki.service` | Create | systemd unit |
| `rpi/src/exceptions.py` | Create | WiFiConnectionError + RtcSyncError removed |
| `rpi/src/config.py` | Create | wifi_settings removed, display_settings added |
| `rpi/src/timezone.py` | Create | zoneinfo replaces manual DST arithmetic |
| `rpi/src/homeassistant.py` | Create | mrequests → requests |
| `rpi/src/nordpool.py` | Copy | Unchanged from pico/src/nordpool.py |
| `rpi/src/healthcheck.py` | Create | WiFi check removed |
| `rpi/src/scheduler.py` | Create | NTP task removed |
| `rpi/src/eink.py` | Create | Full rewrite: luma.epd + Pillow |
| `rpi/src/main.py` | Create | Simplified boot sequence |

All commands run from the repo root unless stated otherwise.

---

## Task 1: Project scaffold

**Files:**
- Create: `rpi/requirements.txt`
- Create: `rpi/.ruff.toml`
- Create: `rpi/config.json.example`

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p rpi/src
```

- [ ] **Step 2: Write `rpi/requirements.txt`**

```text
luma.epd>=0.4.0
Pillow>=9.0.0
requests>=2.28.0
```

- [ ] **Step 3: Write `rpi/.ruff.toml`**

```toml
preview = true

extend-exclude = [
    ".venv",
]

target-version = "py39"
line-length = 100

[lint]
select = [
    "E",
    "W",
    "F",
    "B",
    "SIM",
    "I",
]

extend-select = ["E305"]

ignore = [
    "E501",
]

[format]
quote-style = "double"
indent-style = "space"
```

- [ ] **Step 4: Write `rpi/config.json.example`**

```json
{
  "timezone": {
    "name": "Europe/Helsinki"
  },
  "homeassistant": {
    "url": "http://homeassistant.local:8123",
    "token": "your-long-lived-access-token-here",
    "timeout": 10
  },
  "nordpool": {
    "entity_id": "sensor.nordpool_kwh_fi_eur_3_10_0255",
    "slot_duration": 900,
    "refresh_interval": 14400
  },
  "display": {
    "rst_pin": 17,
    "dc_pin": 25,
    "cs_pin": 8,
    "busy_pin": 24,
    "font_path": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
  }
}
```

> The `display` pin values are Waveshare's conventional BCM numbering for their RPi
> HAT wiring. Adjust to match actual wiring. `font_path` must point to a TTF file
> present on the RPi.

- [ ] **Step 5: Verify the directory exists**

```bash
ls rpi/
```

Expected output includes: `requirements.txt`, `.ruff.toml`, `config.json.example`, `src/`

- [ ] **Step 6: Commit**

```bash
git add rpi/
git commit -m "rpi: add project scaffold"
```

---

## Task 2: exceptions.py

**Files:**
- Create: `rpi/src/exceptions.py`

`NoWifiError` and `RtcSyncError` are removed; the OS owns those failure modes.

- [ ] **Step 1: Write `rpi/src/exceptions.py`**

```python
"""
Error conditions for HAUKI
"""


class HaukiError(RuntimeError):
    def __init__(self, message, detail=""):
        self.message = message
        self.detail = detail
        super().__init__(message)


class NoHomeAssistantError(HaukiError):
    def __init__(self):
        super().__init__("Could not reach HA")


class NoPricesError(HaukiError):
    def __init__(self, detail=""):
        super().__init__("Could not fetch prices", detail)
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python3 -c "import sys; sys.path.insert(0, 'rpi/src'); from exceptions import HaukiError, NoHomeAssistantError, NoPricesError; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rpi/src/exceptions.py
git commit -m "rpi: add exceptions"
```

---

## Task 3: config.py

**Files:**
- Create: `rpi/src/config.py`

`wifi_settings()` is removed. `timezone_settings()` now returns only `{'name': ...}`.
`display_settings()` is added (returns the `display` dict, falling back to `{}`
so default pin values in `eink.py` apply when the section is absent).

Config is loaded relative to the script: `rpi/src/../config.json` → `rpi/config.json`.

- [ ] **Step 1: Write `rpi/src/config.py`**

```python
"""
Configuration loader for HAUKI - Raspberry Pi implementation
"""
import json
import os


class Config:
    def __init__(self, path=None):
        if path is None:
            path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        with open(path) as f:
            self._config = json.load(f)

    def timezone_settings(self):
        return self._config['timezone']

    def homeassistant_settings(self):
        return self._config['homeassistant']

    def nordpool_settings(self):
        return self._config['nordpool']

    def display_settings(self):
        return self._config.get('display', {})
```

- [ ] **Step 2: Create a minimal config.json for local verification**

```bash
cp rpi/config.json.example rpi/config.json
```

Edit `rpi/config.json`: replace the token placeholder with any string (it won't be used yet).

- [ ] **Step 3: Verify Config loads**

```bash
python3 -c "
import sys; sys.path.insert(0, 'rpi/src')
from config import Config
c = Config('rpi/config.json')
print('timezone:', c.timezone_settings())
print('display:', c.display_settings())
print('OK')
"
```

Expected: timezone and display dicts printed, then `OK`.

- [ ] **Step 4: Commit**

```bash
git add rpi/src/config.py
git commit -m "rpi: add config loader"
```

---

## Task 4: timezone.py

**Files:**
- Create: `rpi/src/timezone.py`

`zoneinfo.ZoneInfo` replaces all manual DST arithmetic. The public interface is kept
identical so `nordpool.py` (copied unchanged) can call `now_utc()`,
`parse_iso_timestamp()`, `format_local_time()`, and `is_tomorrow()` without changes.

- [ ] **Step 1: Write `rpi/src/timezone.py`**

```python
"""
Timezone conversion utilities for HAUKI - Raspberry Pi implementation
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


class LocalTimezone:
    def __init__(self, config):
        tz = config.timezone_settings()
        self._tz = ZoneInfo(tz['name'])

    def now_utc(self):
        """Return current time as a UTC integer timestamp."""
        return int(datetime.now(timezone.utc).timestamp())

    def parse_iso_timestamp(self, iso_string):
        """Parse ISO 8601 string (with offset or Z) to UTC integer timestamp."""
        return int(datetime.fromisoformat(iso_string).astimezone(timezone.utc).timestamp())

    def format_local_time(self, utc_timestamp):
        """Convert UTC integer timestamp to local HH:MM string."""
        dt = datetime.fromtimestamp(utc_timestamp, tz=self._tz)
        return f"{dt.hour:02d}:{dt.minute:02d}"

    def is_tomorrow(self, utc_timestamp):
        """Return True if the UTC timestamp falls on tomorrow in local time."""
        today = datetime.now(self._tz).date()
        target = datetime.fromtimestamp(utc_timestamp, tz=self._tz).date()
        return target > today
```

- [ ] **Step 2: Verify the module**

```bash
python3 -c "
import sys; sys.path.insert(0, 'rpi/src')
from config import Config
from timezone import LocalTimezone
c = Config('rpi/config.json')
tz = LocalTimezone(c)
now = tz.now_utc()
print('now_utc:', now)
print('format_local_time:', tz.format_local_time(now))
ts = tz.parse_iso_timestamp('2026-03-11T00:00:00+02:00')
print('parse_iso_timestamp:', ts)
print('OK')
"
```

Expected: integer timestamps and a `HH:MM` string printed, then `OK`.

- [ ] **Step 3: Commit**

```bash
git add rpi/src/timezone.py
git commit -m "rpi: add timezone module (zoneinfo)"
```

---

## Task 5: homeassistant.py

**Files:**
- Create: `rpi/src/homeassistant.py`

`mrequests` is replaced with `requests`. `sys.print_exception` (MicroPython-only)
is replaced with `traceback.print_exc()`. `response.close()` is removed (not needed
with `requests`).

- [ ] **Step 1: Write `rpi/src/homeassistant.py`**

```python
"""
Home Assistant API client for HAUKI - Raspberry Pi implementation
"""
import traceback

import requests


class HomeAssistant:
    def __init__(self, config):
        ha = config.homeassistant_settings()
        self.url = ha['url'].rstrip('/')
        self.token = ha['token']
        self.timeout = ha.get('timeout', 10)
        self.headers = {'Authorization': 'Bearer ' + self.token}
        self.api_endpoint = self.url + '/api/'
        self.states_endpoint_base = self.url + '/api/states/'

    @property
    def is_online(self):
        try:
            response = requests.get(self.api_endpoint, headers=self.headers, timeout=self.timeout)
            return response.status_code == 200
        except Exception:
            traceback.print_exc()
            return False

    def get_entity_state(self, entity_id):
        endpoint = self.states_endpoint_base + entity_id
        try:
            response = requests.get(endpoint, headers=self.headers, timeout=self.timeout)
            if response.status_code != 200:
                print(f"Error: status {response.status_code}")
                return None
            return response.json()
        except Exception:
            traceback.print_exc()
            return None
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import py_compile; py_compile.compile('rpi/src/homeassistant.py', doraise=True); print('OK')"
```

Expected: `OK`

> Full connectivity verification is covered in the on-device section (`make test-ha`).

- [ ] **Step 3: Commit**

```bash
git add rpi/src/homeassistant.py
git commit -m "rpi: add Home Assistant client (requests)"
```

---

## Task 6: nordpool.py

**Files:**
- Create: `rpi/src/nordpool.py`

This module has no MicroPython imports and is copied unchanged.

- [ ] **Step 1: Copy from pico**

```bash
cp pico/src/nordpool.py rpi/src/nordpool.py
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python3 -c "
import sys; sys.path.insert(0, 'rpi/src')
from nordpool import NordPool
print('NordPool imported OK')
"
```

Expected: `NordPool imported OK`

- [ ] **Step 3: Commit**

```bash
git add rpi/src/nordpool.py
git commit -m "rpi: add nordpool (copied from pico, unchanged)"
```

---

## Task 7: healthcheck.py

**Files:**
- Create: `rpi/src/healthcheck.py`

The `wifi` parameter and `NoWifiError` check are removed. `__init__` now takes
only `homeassistant` and `nordpool`.

- [ ] **Step 1: Write `rpi/src/healthcheck.py`**

```python
"""
System health monitoring for HAUKI - Raspberry Pi implementation
"""
from exceptions import NoHomeAssistantError, NoPricesError


class HealthChecker:
    def __init__(self, homeassistant, nordpool):
        self.ha = homeassistant
        self.nordpool = nordpool

    def check(self):
        """Check HA and NordPool health; raise on first failure."""
        if not self.ha.is_online:
            raise NoHomeAssistantError()
        if not self.nordpool.available:
            raise NoPricesError(self.nordpool.unavailability_reason)
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python3 -c "
import sys; sys.path.insert(0, 'rpi/src')
from healthcheck import HealthChecker
print('HealthChecker imported OK')
"
```

Expected: `HealthChecker imported OK`

- [ ] **Step 3: Commit**

```bash
git add rpi/src/healthcheck.py
git commit -m "rpi: add healthcheck (WiFi check removed)"
```

---

## Task 8: scheduler.py

**Files:**
- Create: `rpi/src/scheduler.py`

`six_hour_task()`, `SIX_HOUR_INTERVAL`, `last_six_hour_task`, and the `wifi`
parameter are removed. The core minute loop is unchanged.

- [ ] **Step 1: Write `rpi/src/scheduler.py`**

```python
"""
Task scheduler for HAUKI - Raspberry Pi implementation
"""
import time

MINUTE_INTERVAL = 60


class TaskScheduler:
    def __init__(self, display, health_checker, nordpool, clock):
        self.display = display
        self.health = health_checker
        self.nordpool = nordpool
        self.clock = clock

        self.cheapest_1h = None
        self.cheapest_2h = None
        self.cheapest_4h = None
        # 0 is the sentinel for "no valid slot yet"
        self.last_slot = 0
        self.last_minute_task = 0

    def minute_task(self):
        current_slot = self.nordpool.current_slot
        if current_slot == self.last_slot:
            return
        self.cheapest_1h = self.nordpool.find_cheapest_window(1)
        self.cheapest_2h = self.nordpool.find_cheapest_window(2)
        self.cheapest_4h = self.nordpool.find_cheapest_window(4)
        current_price = self.nordpool.get_current_price()
        if current_price is not None:
            self.last_slot = current_slot
            self.display.show_price(
                current_price,
                self.nordpool.unit,
                self.cheapest_1h,
                self.cheapest_2h,
                self.cheapest_4h,
            )

    def run(self):
        """Main scheduler loop. Does not return under normal operation."""
        while True:
            self.health.check()

            current_time = self.clock.now_utc()

            if current_time - self.last_minute_task >= MINUTE_INTERVAL:
                self.minute_task()
                self.last_minute_task = current_time

            current_time = self.clock.now_utc()
            time_until_next = MINUTE_INTERVAL - (current_time - self.last_minute_task)
            if time_until_next <= 0:
                time_until_next = MINUTE_INTERVAL
            time.sleep(time_until_next)
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python3 -c "
import sys; sys.path.insert(0, 'rpi/src')
from scheduler import TaskScheduler
print('TaskScheduler imported OK')
"
```

Expected: `TaskScheduler imported OK`

- [ ] **Step 3: Commit**

```bash
git add rpi/src/scheduler.py
git commit -m "rpi: add scheduler (NTP task removed)"
```

---

## Task 9: eink.py

**Files:**
- Create: `rpi/src/eink.py`

The largest change. MicroPython's `machine.SPI`, `framebuf`, and the custom `Writer`
library are replaced by `luma.epd` (SPI + display protocol) and Pillow (image
rendering + TTF fonts). The public interface — `show_price()`, `show_error()`,
`show_status()` — is kept identical so `scheduler.py` and `main.py` are unaffected.

> **luma.epd device compatibility note:** The Waveshare 2.13" V4 uses the SSD1680
> controller, same as the V3. The plan uses `epd2in13_V3`. If luma.epd raises an
> error about the display model, check `python3 -c "import luma.epd.device; help(luma.epd.device)"`
> for the list of supported classes and substitute the correct one.

- [ ] **Step 1: Write `rpi/src/eink.py`**

```python
"""
E-ink display driver for HAUKI - Raspberry Pi 1A+ implementation
Waveshare 2.13" V4 (SSD1680 controller) via luma.epd and Pillow
"""
from luma.core.interface.serial import spi
from luma.epd.device import epd2in13_V3
from PIL import Image, ImageDraw, ImageFont

EPD_WIDTH = 250
EPD_HEIGHT = 122

FONT_PATH_DEFAULT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


class Display:
    """Display manager for Waveshare 2.13" V4 e-ink display."""

    def __init__(self, config):
        cfg = config.display_settings()
        serial = spi(
            port=0,
            device=0,
            gpio_DC=cfg.get('dc_pin', 25),
            gpio_RST=cfg.get('rst_pin', 17),
        )
        self.device = epd2in13_V3(serial=serial, gpio_BUSY=cfg.get('busy_pin', 24))
        font_path = cfg.get('font_path', FONT_PATH_DEFAULT)
        self.font48 = ImageFont.truetype(font_path, 48)
        self.font32 = ImageFont.truetype(font_path, 32)
        self.font14 = ImageFont.truetype(font_path, 14)
        self.font12 = ImageFont.truetype(font_path, 12)

    def _new_image(self):
        return Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 255)

    def show_price(self, current_price, unit, cheapest_1h, cheapest_2h, cheapest_4h):
        image = self._new_image()
        draw = ImageDraw.Draw(image)

        draw.text((0, 5), f"{current_price:.2f}", font=self.font48, fill=0)
        draw.text((211, 107), unit, font=self.font14, fill=0)

        time_str, avg_price = cheapest_1h
        draw.text((0, 70), f"{avg_price:.2f} @ {time_str}", font=self.font32, fill=0)

        time_str_2h, avg_price_2h = cheapest_2h
        time_str_4h, avg_price_4h = cheapest_4h
        draw.text(
            (0, 105),
            f"2h: {avg_price_2h:.2f} @ {time_str_2h}  4h: {avg_price_4h:.2f} @ {time_str_4h}",
            font=self.font12,
            fill=0,
        )

        self.device.display(image)

    def show_error(self, message, details=""):
        image = self._new_image()
        draw = ImageDraw.Draw(image)

        draw.text((0, 0), "ERROR", font=self.font32, fill=0)
        draw.text((0, 40), message, font=self.font14, fill=0)
        if details:
            draw.text((0, 60), details, font=self.font12, fill=0)

        self.device.display(image)

    def show_status(self, message):
        image = self._new_image()
        draw = ImageDraw.Draw(image)

        draw.text((0, 50), message, font=self.font14, fill=0)

        self.device.display(image)
```

- [ ] **Step 2: Install dependencies and verify syntax**

```bash
cd rpi && make prepare && cd ..
python3 -c "import py_compile; py_compile.compile('rpi/src/eink.py', doraise=True); print('OK')"
```

Expected: `OK`

> `Display.__init__` touches hardware and will fail outside an RPi with the display
> wired up — the on-device verification section covers that.

- [ ] **Step 3: Commit**

```bash
git add rpi/src/eink.py
git commit -m "rpi: add eink display driver (luma.epd + Pillow)"
```

---

## Task 10: main.py

**Files:**
- Create: `rpi/src/main.py`

The outer loop is simplified: no WiFi connect step, no NTP sync step. systemd's
`Restart=on-failure` handles crashes. The `HealthChecker` is constructed without
a `wifi` argument.

- [ ] **Step 1: Write `rpi/src/main.py`**

```python
"""
Entry point for HAUKI - Raspberry Pi 1A+ implementation
"""
import sys
import time
import traceback

from config import Config
from eink import Display
from exceptions import HaukiError
from healthcheck import HealthChecker
from homeassistant import HomeAssistant
from nordpool import NordPool
from scheduler import TaskScheduler
from timezone import LocalTimezone


if __name__ == "__main__":
    config = Config()
    clock = LocalTimezone(config)
    display = Display(config)
    ha = HomeAssistant(config)
    nordpool = NordPool(ha, clock, config)
    health = HealthChecker(ha, nordpool)
    scheduler = TaskScheduler(display, health, nordpool, clock)

    display.show_status("Starting...")

    while True:
        try:
            scheduler.run()
        except KeyboardInterrupt:
            display.show_status("Stopped")
            sys.exit(0)
        except HaukiError as e:
            traceback.print_exc()
            display.show_error(e.message, e.detail)
            time.sleep(60)
        except Exception as e:
            traceback.print_exc()
            display.show_error("Unexpected error", str(e))
            time.sleep(60)
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import py_compile; py_compile.compile('rpi/src/main.py', doraise=True); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add rpi/src/main.py
git commit -m "rpi: add main entry point"
```

---

## Task 11: Makefile and systemd service

**Files:**
- Create: `rpi/Makefile`
- Create: `rpi/hauki.service`

The service file hardcodes `/opt/hauki/rpi` as the deployment path. Adjust if
deploying elsewhere; the path only matters when running `make install` on the RPi.

- [ ] **Step 1: Write `rpi/hauki.service`**

```ini
[Unit]
Description=HAUKI - Home Assistant Update Kiosk Interface
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hauki
WorkingDirectory=/opt/hauki/rpi
ExecStart=/opt/hauki/rpi/.venv/bin/python src/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Write `rpi/Makefile`**

```makefile
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help
help:
	@echo "HAUKI Raspberry Pi Makefile"
	@echo ""
	@echo "  make prepare   - Create venv, install dependencies"
	@echo "  make lint      - Run Ruff linter on src/"
	@echo "  make test-ha   - Verify Home Assistant connectivity"
	@echo "  make install   - Deploy systemd service (run on the RPi)"
	@echo "  make clean     - Remove venv and caches"

.PHONY: prepare
prepare:
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
		$(PIP) install --upgrade pip; \
		$(PIP) install -r requirements.txt; \
		echo "✓ venv created and dependencies installed"; \
	fi

.PHONY: lint
lint: prepare
	$(VENV)/bin/ruff check src/

.PHONY: test-ha
test-ha: prepare
	@if [ ! -f config.json ]; then \
		echo "Error: config.json not found. Copy config.json.example and edit it."; \
		exit 1; \
	fi
	$(PYTHON) -c "\
import sys; sys.path.insert(0, 'src'); \
from config import Config; \
from homeassistant import HomeAssistant; \
ha = HomeAssistant(Config()); \
print('HA online:', ha.is_online)"

.PHONY: install
install:
	@if [ ! -f config.json ]; then \
		echo "Error: config.json not found. Copy config.json.example and edit it first."; \
		exit 1; \
	fi
	sudo useradd -r -s /bin/false hauki 2>/dev/null || true
	sudo usermod -a -G spi,gpio hauki
	sudo cp hauki.service /etc/systemd/system/hauki.service
	sudo systemctl daemon-reload
	sudo systemctl enable hauki
	sudo systemctl start hauki
	@echo "Service installed. Check status: sudo systemctl status hauki"
	@echo "Follow logs: sudo journalctl -u hauki -f"

.PHONY: clean
clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete"
```

- [ ] **Step 3: Verify the Makefile is syntactically valid**

```bash
make -n -f rpi/Makefile help
```

Expected: prints the help text (dry-run, no side effects).

- [ ] **Step 4: Run the linter across all rpi/src/ files**

```bash
cd rpi && make lint
```

Fix any Ruff warnings before committing.

- [ ] **Step 5: Commit**

```bash
git add rpi/Makefile rpi/hauki.service
git commit -m "rpi: add Makefile and systemd service unit"
```

---

## Post-implementation: On-device verification

Run these steps on the Raspberry Pi after deploying the code to `/opt/hauki/rpi/`.

- [ ] **Clone/copy the repo and set up**

```bash
sudo mkdir -p /opt/hauki
sudo chown $USER:$USER /opt/hauki
cd /opt/hauki && git clone <repo-url> hauki
cd /opt/hauki/hauki/rpi
cp config.json.example config.json
# Edit config.json: set your HA URL, token, entity_id, and verify pin wiring
make prepare
```

- [ ] **Verify HA connectivity**

```bash
make test-ha
```

Expected: `HA online: True`

- [ ] **Test the display initialises (requires display wired up)**

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, 'src')
from config import Config
from eink import Display
d = Display(Config())
d.show_status('Test OK')
print('Display init OK')
"
```

Expected: display shows "Test OK", no exceptions.

- [ ] **Install the systemd service**

```bash
make install
sudo systemctl status hauki
```

Expected: service active and running.

- [ ] **Check logs for first price update**

```bash
sudo journalctl -u hauki -f
```

Expected: no errors; display updates once prices are fetched.
