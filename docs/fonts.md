# Fonts in HAUKI

HAUKI uses four DejaVu Sans font sizes compiled into MicroPython modules via
Peter Hinch's [micropython-font-to-py](https://github.com/peterhinch/micropython-font-to-py) tool.

## Font sizes and usage

| Module | Size | Used for |
|--------|------|----------|
| `fonts/font48.py` | 48 pt | Current electricity price (digits only: `0123456789.-`) |
| `fonts/font32.py` | 32 pt | Cheapest 1h window |
| `fonts/font14.py` | 14 pt | Unit label, cheapest 2h/4h row, status/error messages |
| `fonts/font12.py` | 12 pt | Cheapest 2h/4h detail row |

font48 is hardcoded in `make fonts` with a digits-only charset to keep the
file small. The other three sizes are generated from `FONT_SIZES` in `config.mk`
with a full charset that includes Finnish letters (äöåÄÖÅ).

## Generating fonts

```bash
make fonts
```

This requires `FONT_PATH` and `FONT_SIZES` to be set in `config.mk`.
See `config.mk.example` for the expected values. The fonts are written to
`lib/fonts/` and uploaded as part of `make upload`.

## Changing the font

Set `FONT_PATH` in `config.mk` to any TrueType font file and run `make fonts`.
DejaVu Sans is the default because it is pre-installed on most Linux systems
and covers the Finnish characters the project needs.

## Changing font sizes

Changing `FONT_SIZES` in `config.mk` only affects which files get generated;
the layout in `src/eink.py` (`PriceDisplay`) uses hardcoded pixel coordinates
tailored to the specific sizes above. If sizes change, the `set_textpos` calls
in `show_price()`, `show_error()`, and `show_status()` must be updated to match.
