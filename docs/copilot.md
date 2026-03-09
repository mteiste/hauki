# GitHub Copilot in Hauki Development

This document traces the complete development history of the Hauki project — a Raspberry Pi
Pico W device that fetches Nordpool electricity prices and displays them on a Waveshare 2.13"
e-ink display, with Home Assistant integration and automatic DST-aware timezone conversion.

The developer designed the architecture incrementally — deciding what each class would own,
what it would receive as dependencies, and how it would connect to the rest of the system —
one component at a time. **Copilot (Claude Sonnet 4.6) wrote every line of code.**

---

## How Copilot Wrote the Entire Project

The developer's contribution was direction: designing the architecture class by class,
pushing back on over-engineering, and confirming plans before permanent changes. Every line
of code, every config file, every Makefile target, and every document was written by Copilot.
Specific patterns that enabled this:

**Incremental, class-by-class architecture.** The application was never prompted as a whole.
The developer defined the system one component at a time, in roughly this order: build system
and toolchain → `EPD_Landscape` (display driver, forked from vendor code) → `Config`
(configuration loading) → `WiFi` (connection management and NTP sync) → `LocalTimezone`
(DST-aware time conversion) → `NordPool` and `HomeAssistant` (data fetching) →
`TaskScheduler` (composing everything into a run loop) → `HealthChecker` (guarding each
iteration) → `PriceDisplay` (translating data into display output) → exception hierarchy
(`HaukiError` and subclasses). At each step the developer specified what the class would own,
what it would receive as constructor arguments, and how the caller would use it. Copilot's
role was implementation within those constraints, not design.

**Architectural reasoning without prompting.** Copilot detected the 80% code duplication in
the display driver independently and proposed the Template Method pattern. It diagnosed that
`time.localtime()` does not timezone-convert in MicroPython and built a complete custom
implementation. It identified the 3 812-call SPI bottleneck and rewrote it before the
developer noticed.

**Iterative refinement driven by developer pushback.** The WiFi class went through 9 prompts
of simplification. The Config class was cut from 10+ speculative methods to 2. The main loop
was rebuilt three times as the architecture matured. Copilot never resisted simplification —
each pushback produced cleaner code.

**Code quality gatekeeping by the developer.** All generated code was carefully reviewed
before acceptance. The developer repeatedly pushed back on implementation details until the
code met the project's standards. Copilot showed a consistent tendency to produce overly
general solutions, unnecessarily verbose code, and resource-wasteful patterns — problematic
on a microcontroller with constrained RAM and CPU. It also reached for naive algorithms when
tighter ones were available. The developer identified these issues across sessions and required
revisions until the result was deemed acceptable. The `.instructions.md` file was extended
throughout the project to encode lessons learned and prevent the same patterns from
recurring.

**Self-correcting debugging.** The `make reset` target was wrong twice before landing on a
working approach. The Waveshare driver was initially downloaded from the wrong repository.
The Makefile had a tab/space separator bug. The VS Code linter was broken because of a
missing extension. In each case Copilot diagnosed the root cause, not just the symptom.

**Project convention enforcement.** Copilot wrote `.instructions.md` (now
`.github/copilot-instructions.md`) from the first session and updated it throughout development
— encoding "no progress logging", "no defensive coding", "imports at top level", and
"present plans before permanent changes". In later sessions Copilot enforced these rules
against its own earlier work.

**No developer code.** Not a single line of production code, Makefile recipe, config schema,
or documentation sentence was typed by the developer. The developer's input was entirely
natural language: what the project should do and what it should not do.

---

## Project at a Glance

| | |
|---|---|
| **Period** | March 8–14, 2026 (7 days) |
| **Sessions** | 15 documented sessions |
| **Total prompts** | ~188 |
| **Developer code** | 0 lines |
| **Copilot code** | All production code, config, Makefile, and documentation |

---

## Project Timeline

```text
March 8   ── Session 1:  Development environment and build system       (22 prompts)
          ── Session 2:  E-paper display driver integration              (14 prompts)
          ── Session 3:  VS Code linter fix (Ruff extension)             ( 6 prompts)

March 9   ── Session 4:  Display hardware documentation                  ( 4 prompts)
          ── Session 5:  E-ink driver refactoring + Template Method      (20 prompts)
          ── Session 6:  Debugging and Makefile enhancements             (16 prompts)
          ── Session 7:  PEP8 naming + SPI performance optimization      ( 4 prompts)
          ── Session 8:  License compliance (MIT in GPLv3 project)       ( 4 prompts)
          ─┐ Session 9:  Configuration system + smart display API        (12 prompts)
March 14  ─┘  (multi-day, March 9–14)

March 11  ── Session 10: WiFi module + src/ directory restructuring      (17 prompts)
          ── Session 11: NTP sync + timezone + DST support               (14 prompts)
          ─┐ Session 12: Custom fonts with Finnish character support     (17 prompts)
March 14  ─┘  (multi-day, March 9–14)

March 12  ── [Application core: Nordpool, HomeAssistant, scheduler,
              healthcheck — no individual session file documented]

March 13  ── Session 13: Code quality, exception analysis, architecture  (20 prompts)
          ── Session 14: Font optimization + RTC error propagation       ( 3 prompts)

March 14  ── Session 15: Documentation overhaul + README cleanup         (15 prompts)
```

**Total: ~188 prompts across 15 documented sessions over 7 days.**

---

## Development Stages

### Stage 1 — Foundation (March 8, ~42 prompts)

Established the complete development toolchain from zero.

**What Copilot built:**

- `Makefile` from scratch with `prepare`, `upload`, `lint`, `clean`, `reset`, `monitor`, `ls`
  targets — including the "no magic defaults" pattern that fails loudly if `config.mk` is absent
- Python virtual environment wired to `adafruit-ampy`, `ruff`, MicroPython stubs, and `mypy`
- Node.js installed locally in `.nodejs/` with `markdownlint-cli2` via `package.json`
- `.vscode/settings.json` and `.vscode/extensions.json` for MicroPython-aware Pylance and Ruff
- `config.mk` / `config.mk.example` pattern for host-specific secrets (gitignored)
- `.gitignore`, `LICENSE` (GPLv3), `.instructions.md` encoding project philosophy
- Waveshare MicroPython driver downloaded by `make prepare` from the correct Pico-specific
  repository (`waveshareteam/Pico_ePaper_Code`) after an initial wrong-repo mistake (Linux drivers)
- First working "Hello World" rendered on the e-ink display
- VS Code Ruff integration repaired — root cause diagnosed as a missing extension, not config

**Key decisions shaped by Copilot:**

- Chose `ampy` over `rshell` (simpler, file-focused)
- Chose `ruff` over `flake8` (MicroPython-compatible, faster)
- Proposed and implemented the silent idempotent `make prepare` pattern
- `lib/` excluded from linting (third-party code)

---

### Stage 2 — Display Driver Ownership (March 9, ~44 prompts)

Took full ownership of the vendor display driver and transformed it into clean project code.

**What Copilot built:**

- Cloned and analysed the 719-line Waveshare driver; identified 8 debug print statements,
  naming inconsistencies (PascalCase/camelCase), and a typo ("documnetation")
- Forked to `eink.py` in the project root with MIT attribution header; applied `ruff --fix`
  (165 formatting fixes); reduced to 635 lines
- Detected ~80% code duplication between `EPD_Portrait` and `EPD_Landscape` classes
- Applied the **Template Method pattern** (Gang of Four): extracted `EPD` base class with three
  override points — `_get_framebuf_params()`, `_get_data_entry_mode()`,
  `_send_display_buffer()` — reducing total lines to 405 (36% reduction, 230 lines eliminated)
- Renamed classes from version-specific `EPD_2in13_V4_Portrait/Landscape` to clean
  `EPD_Portrait / EPD_Landscape`
- PEP8 compliance: renamed 8 methods from PascalCase/camelCase to snake_case
- Performance: the landscape `_send_display_buffer()` was calling `send_data()` 3 812 times
  (one per byte). Copilot profiled this, identified it as ~1 000× excessive GPIO toggling and
  ~3 800× excessive SPI transactions, rewrote the method to reorder pixels into a pre-allocated
  buffer and dispatch a **single** `send_data1()` call — 99.97% reduction in SPI transactions
- Diagnosed the `display()` missing buffer argument runtime crash
- Switched orientation from Portrait (122×250) to Landscape (250×122)
- Created hardware reference documentation: `docs/eink_display.md` covering coordinate system,
  MONO_VLSB buffer layout, refresh mode selection, and the transpose algorithm
- `LICENSES/WAVESHARE-ATTRIBUTION.txt` created; confirmed MIT-in-GPLv3 compatibility
- `make reset` debugged through three iterations (inline → stdin pipe → temp file) before a
  reliable solution was found; Makefile tab-vs-space bug fixed; module naming constraint
  (hyphens invalid) identified and file renamed

**Key Copilot contributions:**

- Independently detected the duplication without being asked
- Proposed the Template Method pattern and executed the full three-phase refactor
- Profiled GPIO operations to justify and implement the buffered SPI approach

---

### Stage 3 — Configuration, Display API, and Boot Safety (March 9–14, ~12 prompts)

Designed the project's configuration architecture and a smart display refresh API.

**What Copilot built:**

- `config.json` / `config.json.example` schema and `Config` class in `src/config.py`
- Iterated the Config API through four phases: standalone functions → class with many methods →
  simplified to two essential methods (`__init__`, `wifi_settings()`) after the developer pushed
  back on speculative accessors
- Smart `display(image, mode='auto')` method: tracks `_refresh_counter`, runs full refresh on
  first call and every 10 thereafter, fast refresh in between — eliminating all manual refresh
  management from call sites
- `boot.py` stripped of all hardware dependencies (no display, no imports beyond bare minimum)
  to prevent boot crashes from locking out the REPL
- Comprehensive docstrings written for all 24 functions in `eink.py`

---

### Stage 4 — Custom Fonts with Finnish Support (March 9–14, ~17 prompts)

Added a full custom font pipeline for non-ASCII character display.

**What Copilot built:**

- Verified that the built-in 8×8 framebuffer font covers only ASCII 32–127 (no Finnish ä ö å)
- Selected Peter Hinch's `micropython-font-to-py` toolchain with DejaVu Sans
- `make fonts` target generating sizes 12, 14, 32 pt (sparse, full Latin+Finnish charset)
  plus a dedicated 48 pt numbers-only font for the price display
- `lib/writer.py` and `lib/writer.pyi` (auto-generated stub) for IDE autocomplete
- Fixed font path bug (absolute paths fail Python identifier validation)
- Fixed e-ink colour inversion (Writer's monochrome mode requires `invert=True`)
- `freetype-py==2.4.0` added to requirements
- `make prepare` extended to set up font-to-py silently

---

### Stage 5 — Networking and Time (March 11, ~31 prompts)

Built the full networking stack and timezone-aware time system.

**What Copilot built:**

- `src/wifi.py` — `WiFi` class iterated through 9 prompts of refinement:
  standalone functions → class → required constructor config → `connect()` returns `bool` →
  individual properties (`ssid`, `ip_address`, `rssi`) replacing a `status()` dict →
  `is_active` removed as redundant with `is_connected`
- `sync_rtc()` in `WiFi`: NTP sync via MicroPython's built-in `ntptime` module
- `src/timezone.py` — `LocalTimezone` class built entirely from scratch because MicroPython
  has no `datetime` module and `time.localtime()` does not actually convert timezones:
  - `utc_to_local()` — converts RTC 8-tuple to local time
  - `_is_dst()` — evaluates active DST rules from config
  - `_find_nth_weekday()` — calculates DST transition dates (including "last Sunday")
  - `_days_in_month()` — full month-length arithmetic with leap-year handling
- Timezone configuration in `config.json` with fully externalised DST rules
  (month, week, weekday, hour) supporting any world timezone
- `src/` directory created; Makefile rewritten to auto-discover all `*.py` files
  in `src/` — eliminating the class of bug where a new module gets forgotten from upload
- All imports verified at module top level (MicroPython constraint)

**Key Copilot contributions:**

- Recognised `time.localtime()` does not timezone-convert in MicroPython and built a
  complete manual implementation
- Designed configuration-driven DST rules that will survive timezone policy changes without
  code edits

---

### Stage 6 — Application Core (March 12, undocumented)

The Nordpool, Home Assistant, scheduler, and health-check modules were implemented in this
period. No individual session file was created, but all four files exist in `src/` and are
referenced extensively in the Session 13 quality review:

- `src/nordpool.py` — fetches and parses hourly electricity prices via the Nordpool API
- `src/homeassistant.py` — queries Home Assistant entity states
- `src/scheduler.py` — runs tasks on minute, hourly, and six-hour intervals
- `src/healthcheck.py` — checks WiFi and RTC health before each scheduler iteration
- `src/exceptions.py` — shared exception types
- `src/eink.py` extended with `PriceDisplay` class: shows current price (font48), cheapest
  1h/2h/4h windows, and unit labels

---

### Stage 7 — Architecture Hardening (March 13, ~20 prompts)

Systematic quality and correctness pass across the entire codebase.

**What Copilot did:**

- Full exception trace through every `src/` file; identified five uncaught-or-risky paths:
  - `healthcheck.check()` → `wifi.is_connected` → `OSError` (uncaught)
  - `nordpool._refresh()` → `parse_iso_timestamp()` `.split()` unpacking → `ValueError`
  - `eink.show_price()` unpacking `None` cheapest windows → `TypeError` before first hourly run
  - `wifi.connect()` propagating `OSError` from hardware
  - `eink._read_busy()` busy-wait with no timeout (infinite hang on hardware fault)
- `HomeAssistant.is_online()` converted from method to `@property`
- `HealthCheckError` moved from `scheduler.py` to `healthcheck.py` (correct ownership)
- `healthcheck.check()` refactored to raise `HealthCheckError` instead of returning int
- Health check centralised at the top of the `scheduler.run()` loop; individual tasks no
  longer check WiFi themselves
- Main loop restructured for indefinite operation:
  all class instantiation outside the loop; all exceptions caught with `show_error()` +
  60 s sleep + retry — device never halts on any error
- `TaskScheduler` receives `clock` parameter; all `time.time()` calls replaced with
  `self.clock.now_utc()` to route through the timezone abstraction
- Task order comment added explaining the six-hour → hourly → minute dependency chain
- Imports at module top level enforced; this rule added to permanent Copilot memory

---

### Stage 8 — Error Propagation and Font Tuning (March 14, ~3 prompts)

Small but targeted improvements to error handling and display layout.

**What Copilot built:**

- `RTC_SYNC_FAILED = 5` error constant; `six_hour_task()` raises `HealthCheckError` instead
  of silently catching NTP failure
- `main.py` handler: RTC failure triggers WiFi reconnect and retries
- Exception chaining (`raise ... from e`) for debugging context
- Font charset refined: standard fonts get `@` for time display; `font48` and `font64` use
  numbers-only charset `"0123456789.-"` — `make fonts` regenerated all fonts

---

### Stage 9 — Documentation Overhaul (March 13–14, ~15 prompts)

Complete rewrite of project documentation to reflect the actual codebase.

**What Copilot produced:**

- `src/README.md` — architecture document: boot sequence, component diagram, time/slot model,
  health-check loop, error handling strategy, DST rules, key assumptions
- `docs/eink_display.md` (rewritten) — `EPD_Landscape` coordinate system, MONO_VLSB layout,
  128-pixel padding, refresh counter logic, `_send_display_buffer` transpose algorithm
- `docs/display_rendering.md` (new) — FrameBuffer → EPD pipeline, MONO_VLSB memory layout,
  Writer glyph rendering, `invert=True` mechanics, full update sequence
- `docs/fonts.md` (rewritten from `custom-fonts-guide.md`) — project-specific: which fonts,
  what sizes, what they display, how to regenerate
- `LICENSES/DEJAVU` — added DejaVu Sans (Bitstream Vera) attribution
- `README.md` — setup order corrected, developer workflow sections removed, structure
  simplified, config schema updated to match actual `config.json.example`
- Markdown lint reduced from 267 errors to 0 across all docs
- Removed `docs/eink-library-guide.md` (described old upstream API, not current code)
- Unused `font64` import and `wri64` writer removed from `eink.py`; Makefile font generation
  pruned to match actual usage (sizes 12, 14, 32 + hardcoded 48)

---

## Total Prompt Breakdown by Session

| # | Session | Date | Prompts |
|---|---------|------|---------|
| 1 | Development environment and build system | Mar 8 | 22 |
| 2 | E-paper display driver integration | Mar 8 | 14 |
| 3 | VS Code Ruff linter fix | Mar 8 | 6 |
| 4 | Display hardware documentation | Mar 9 | 4 |
| 5 | E-ink driver refactoring + Template Method pattern | Mar 9 | 20 |
| 6 | Debugging and Makefile enhancements | Mar 9 | 16 |
| 7 | PEP8 naming + SPI performance optimisation | Mar 9 | 4 |
| 8 | License compliance (MIT in GPLv3 project) | Mar 9 | 4 |
| 9 | Configuration system + smart display API | Mar 9–14 | 12 |
| 10 | WiFi module + `src/` directory restructuring | Mar 11 | 17 |
| 11 | NTP sync + timezone + DST support | Mar 11 | 14 |
| 12 | Custom fonts with Finnish character support | Mar 9–14 | 17 |
| 13 | Code quality, exception analysis, architecture hardening | Mar 13 | 20 |
| 14 | Font optimisation + RTC error propagation | Mar 14 | 3 |
| 15 | Documentation overhaul + README cleanup | Mar 13–14 | 15 |
| | **Total** | | **~188** |
