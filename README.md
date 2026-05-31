# HAUKI - Home Assistant Update Kiosk Interface

HAUKI fetches hourly Nordpool electricity spot prices and displays them on a
Waveshare 2.13" e-ink display. The practical purpose is to have an always-visible,
at-a-glance view of the current electricity price and the cheapest 1h, 2h, and 4h
windows ahead — making it easy to decide the best time to run high-consumption
appliances like washing machines, dishwashers, or ovens.

The project is also an experiment in agent-based software development: every line of
production code, configuration, Makefile, and documentation was written by a coding
agent (GitHub Copilot / Claude Code). The developer's role was architecture and
direction — deciding what each component would do and how it would connect to the rest
of the system — with no code typed by hand.

## Platforms

The same display and Home Assistant integration runs on two hardware platforms.
Each is a fully independent implementation in its own directory.

| Platform | Directory | Runtime | Status |
|----------|-----------|---------|--------|
| Raspberry Pi Pico W | [`pico/`](pico/) | MicroPython | Complete |
| Raspberry Pi 1A+ | [`rpi/`](rpi/) | CPython | In progress |

## Repository Structure

```text
.
├── pico/                # Raspberry Pi Pico W implementation (MicroPython)
├── rpi/                 # Raspberry Pi 1A+ implementation (CPython)
├── docs/                # Domain documentation (display, fonts, development history)
└── LICENSE              # GPLv3
```

See each platform directory for setup instructions, configuration, and build targets.

## About the Agent-Based Development Experiment

This project was the primary rule of the experiment, set upfront and held throughout:
no developer writes code. The motivation was twofold.

First, to understand the real limitations of agent-based coding — not from a "write an
application that does X" prompt, but from deliberate, structured use. Having seen the
results of that kind of prompting produce unmaintainable code, the goal was to find out
whether a disciplined, incremental approach — one class at a time, with full review
before acceptance — could produce something worth keeping. The agent never had the final
decision on anything. Every implementation detail had to pass review, and many were
pushed back on and revised until they met the project's standard.

Second, this project had been sitting in the backlog for a long time — the e-ink display
was bought roughly a year before development started. It never got implemented because,
while useful, it offered no real learning opportunity: the technical side of it would
have been a routine small embedded project. Agent-based coding made it interesting again.

[docs/copilot.md](docs/copilot.md) traces the full development history of the Pico
implementation. It was, of course, also written by the agent.

## License

This project is licensed under GPLv3. See [LICENSE](LICENSE) for details.

Third-party components retain their original licenses; see the `LICENSES/` directory
inside each platform directory.
