# HAUKI - Home Assistant Update Kiosk Interface

HAUKI is a Raspberry Pi Pico W device that fetches hourly Nordpool electricity spot prices
and displays them on a Waveshare 2.13" e-ink display. The practical purpose is to have a
always-visible, at-a-glance view of the current electricity price and the cheapest 1h, 2h,
and 4h windows ahead — making it easy to decide the best time to run high-consumption
appliances like washing machines, dishwashers, or ovens.

The project is also an experiment in agent-based software development: every line of
production code, configuration, Makefile, and documentation was written by GitHub Copilot
(Claude Sonnet 4.6). The developer's role was architecture and direction — deciding what
each component would do and how it would connect to the rest of the system — with no code
typed by hand.

## Why no developer code?

This was the primary rule of the experiment, set upfront and held throughout. The motivation
was twofold.

First, to understand the real limitations of agent-based coding — not from a "write an
application that does X" prompt, but from deliberate, structured use. Having seen the results
of that kind of prompting produce unmaintainable code, the goal was to find out whether a
disciplined, incremental approach — one class at a time, with full review before acceptance —
could produce something worth keeping. Copilot never had the final decision on anything.
Every implementation detail had to pass review, and many were pushed back on and revised
until they met the project's standard.

Second, this project had been sitting in the backlog for a long time — the e-ink display was
bought roughly a year before development started. It never got implemented because, while
useful, it offered no real learning opportunity: the technical side of it would have been a
routine small embedded project. Agent-based coding made it interesting again.

## Was it worth it?

The final code is good enough. Left entirely to its own devices, Copilot would likely have
produced something worse — it has a consistent tendency toward overly general, verbose, and
resource-wasteful solutions. The quality in the end is a direct result of the developer
staying in the loop and refusing to accept the first answer.

Would this approach work for a real production project? No. For a project of this scale and
definition, with zero need for handoff to others, it worked well. The zero-developer-code
constraint was never the point — learning the limits of the tool was.

[docs/copilot.md](docs/copilot.md) traces the full development history of the project.
It was, of course, also written by Copilot.

## Was it faster?

Yes and no.

Yes, in the sense that this project had been sitting in the backlog for a long time with no
sign of ever getting done. Whether that counts as "faster" is debatable, but it shipped —
and that is the only metric that matters for a backlog item.

No, in the sense of raw time. The project took around 25 hours spread across 7 days. Writing
the same thing manually — excluding documentation — would have taken roughly 4 to 6 hours
for a first working iteration, plus some additional hours for testing and debugging. Agent-based
development was slower, not faster.

The overhead comes from the nature of the process: every generated output has to be read,
understood, and evaluated before it can be accepted. There is no skimming. When Copilot
produces something subtly wrong or needlessly complex, catching it takes longer than just
writing the correct thing directly would have. The more familiar you are with the domain,
the more pronounced this gap becomes.

## Hardware Requirements

- Raspberry Pi Pico or Pico W
- E-ink display (e.g., Waveshare, Pimoroni Inky)
- USB cable for programming and power
- Connection cables/headers for display

## Setup

1. **Configure Build Environment:**

   ```bash
   cp config.mk.example config.mk
   # Edit config.mk and set your Pico's serial PORT and font path
   ```

2. **Configure Device Settings:**

   ```bash
   cp config.json.example config.json
   # Edit config.json with your WiFi and Home Assistant settings
   ```

3. **Install Development Tools:**

   ```bash
   make prepare
   ```

4. **Upload Files to Pico:**

   ```bash
   make upload
   ```

## Project Structure

```text
.
├── src/                 # Device code (uploaded to Pico)
├── lib/                 # Generated libraries (fonts, mrequests, writer)
├── tools/               # Development and testing scripts
├── docs/                # Documentation
├── config.json          # Device configuration (create from .example, not in git)
├── config.json.example  # Template for device configuration
├── config.mk            # Build configuration (create from .example, not in git)
├── config.mk.example    # Template for build configuration
└── Makefile             # Build and upload automation
```

## Configuration

### Build Configuration (`config.mk`)

Controls the development environment, serial port, and font path:

```makefile
# Serial port for Pico connection
PORT = /dev/ttyACM0

# Font for display text (for custom fonts)
FONT_PATH = /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
```

### Device Configuration (`config.json`)

Runtime settings for the Pico (WiFi, timezone, Home Assistant, Nord Pool):

```json
{
  "wifi": {
    "ssid": "YourNetworkName",
    "password": "YourWiFiPassword",
    "timeout": 10
  },
  "timezone": {
    "name": "Europe/Helsinki",
    "std_offset": 2,
    "dst_offset": 3,
    "dst_rules": {
      "start": { "month": 3, "week": -1, "weekday": 6, "hour": 3 },
      "end":   { "month": 10, "week": -1, "weekday": 6, "hour": 4 }
    }
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
  }
}
```

Both files are git-ignored for security. Use the `.example` templates to create your own.

See `make help` for all available commands.

## Third-Party Libraries

This project uses the following third-party libraries:

### Waveshare Pico ePaper Driver

- **Source**: [Waveshare Pico_ePaper_Code](https://github.com/waveshare/Pico_ePaper_Code)
- **License**: MIT License
- **Usage**: E-paper display driver (refactored to `eink.py`)
- **Attribution**: See [LICENSES/WAVESHARE](LICENSES/WAVESHARE)

### mrequests - HTTP Client for MicroPython

- **Source**: [SpotlightKid/mrequests](https://github.com/SpotlightKid/mrequests)
- **License**: MIT License
- **Usage**: HTTP client library for Home Assistant API communication
- **Attribution**: See [LICENSES/MREQUESTS](LICENSES/MREQUESTS)

### micropython-font-to-py - Font Conversion Tools

- **Source**: [peterhinch/micropython-font-to-py](https://github.com/peterhinch/micropython-font-to-py)
- **License**: MIT License
- **Usage**: Font conversion tools and Writer library for text rendering on e-ink display
- **Attribution**: See [LICENSES/MICROPYTHON-FONT-TO-PY](LICENSES/MICROPYTHON-FONT-TO-PY)

### DejaVu Sans - Display Font

- **Source**: [dejavu-fonts.github.io](https://dejavu-fonts.github.io/)
- **License**: Bitstream Vera Fonts License
- **Usage**: Font used for display text, compiled into `lib/fonts/` via `make fonts`
- **Attribution**: See [LICENSES/DEJAVU](LICENSES/DEJAVU)

## Custom Fonts

See [docs/fonts.md](docs/fonts.md).

## License

This project is licensed under GPLv3. See [LICENSE](LICENSE) for details.

Third-party components retain their original licenses (see [LICENSES/](LICENSES/) directory).

## Resources

### Documentation

- [Custom Fonts Guide](docs/fonts.md) - Using variable fonts and Finnish characters
- [Hardware Documentation](docs/eink_display.md) - E-ink display driver reference
- [Display Rendering](docs/display_rendering.md) - FrameBuffer, Writer and font interaction

### External Resources

- [MicroPython Documentation](https://docs.micropython.org/)
- [Raspberry Pi Pico Python SDK](https://datasheets.raspberrypi.com/pico/raspberry-pi-pico-python-sdk.pdf)
- [Pico Pinout](https://pico.pinout.xyz/)
- [font-to-py Tool](https://github.com/peterhinch/micropython-font-to-py) - Font generation for MicroPython
