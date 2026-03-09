# E-Ink Display Driver (`EPD_Landscape`)

Documents the `EPD_Landscape` class in `src/eink.py`. Derived from the
Waveshare Pico_ePaper-2.13_V4.py driver (see `LICENSES/WAVESHARE`).

## Hardware

- **Display:** Waveshare 2.13" e-Paper V4
- **Physical orientation:** Portrait (122 × 250 pixels, hardware scan order)
- **Software orientation:** Landscape (250 × 122) — rotated by the driver
- **Interface:** SPI1 at 4 MHz

| Signal | GPIO |
|--------|------|
| RST | 12 |
| DC | 8 |
| CS | 9 |
| BUSY | 13 |
| MOSI | 11 (SPI1) |
| SCK | 10 (SPI1) |

## Coordinate system

The physical hardware scans in portrait orientation (X=0–121 across the
122 px axis, Y=0–249 down the 250 px axis). `EPD_Landscape` presents the
display to application code as 250 wide × 122 tall (landscape). The driver
performs the transpose internally before each SPI transfer.

`self.width = 250`, `self.height = 122` — these are the values the Writer
library and application code use for pixel addressing.

## Framebuffer layout

The FrameBuffer is initialised with `MONO_VLSB` format:

- Each byte represents a vertical column of 8 pixels.
- Bit 0 (LSB) is the topmost pixel of the column.
- In the landscape coordinate system, bytes advance left-to-right along
  the 250 px width, then top-to-bottom in groups of 8 px.

The buffer is sized to the **physical** dimensions:
`250 * 128 / 8 = 4000 bytes` (122 is rounded up to the next multiple of 8, i.e. 128).
A second `_reordered_buffer` of the same size is allocated for the transpose.

## Landscape-to-portrait transpose

`_send_display_buffer()` rewrites the MONO_VLSB landscape buffer into the
hardware's expected portrait scan order before sending over SPI.

The loop:

```python
for j in range(width_bytes - 1, -1, -1):   # column groups, reversed
    for i in range(0, self._physical_height):  # rows
        self._reordered_buffer[idx] = image[i + j * self._physical_height]
```

Iterates over column-bytes in reverse and pulls the corresponding row bytes,
effectively rotating 90 degrees. Without this step the image would appear
rotated and/or mirrored on the physical display.

## Initialisation sequence

`__init__` performs the following in order:

1. Set up GPIO pins (RST out, BUSY in pull-up, CS out, DC out).
2. Compute physical width rounded up to byte boundary.
3. Allocate `buffer` and `_reordered_buffer`.
4. Set `self.width / height` to landscape values, call `FrameBuffer.__init__`.
5. Set `_refresh_counter = REFRESH_THRESHOLD` so the first `display()` call
   triggers a full refresh.
6. Hardware reset via RST pin (HIGH 20 ms → LOW 2 ms → HIGH 20 ms).
7. Wait for BUSY LOW, send SWRESET (0x12), wait for BUSY LOW again.
8. Configure driver output control (0x01), data entry mode (0x11, value 0x07
   = Y increment, X increment, Y-major address scan).
9. Set RAM window and cursor to the full 122 × 250 area.
10. Set border waveform (0x3C), display update control (0x21), enable
    built-in temperature sensor (0x18).
11. Wait for BUSY LOW — display is ready.

## Refresh modes

| Mode | Controller command | Duration | Use |
|------|--------------------|----------|-----|
| `UPDATE_FULL` (`0xF7`) | Full waveform | ~2 s | First call, periodic ghosting clear |
| `UPDATE_FAST` (`0xC7`) | Abbreviated waveform | ~1 s | Subsequent updates |

`display()` selects automatically via `_refresh_counter`:

- Counter starts at `REFRESH_THRESHOLD` (10) so the first call is always full.
- After each full refresh the counter resets to 0.
- After each fast refresh the counter increments.
- When the counter reaches `REFRESH_THRESHOLD` again, the next call is full.

`clear()` also resets the counter to `REFRESH_THRESHOLD`, so clearing always
precedes a full refresh on the next `display()` call.

## `_display_base()`

Writes the same image to both display RAM banks (0x24 and 0x26) and performs
a full refresh. This is the recommended initialisation step for partial-refresh
scenarios (ensures both banks are in sync), but HAUKI does not currently use
partial refresh.

## BUSY pin polarity

The BUSY pin is HIGH while the controller is busy. `_read_busy()` polls
until the pin goes LOW. The pin is configured with `PULL_UP` to avoid
floating reads before initialisation.

## Width padding

`EPD_WIDTH = 122` is not divisible by 8. The driver rounds it up to 128:

```python
if EPD_WIDTH % 8 == 0:
    self._physical_width = EPD_WIDTH
else:
    self._physical_width = (EPD_WIDTH // 8) * 8 + 8
```

Buffer addressing uses 128 as the stride, but the hardware window
(`_set_windows`) is still told the actual physical extent.

## Pin connections reference

```text
RST_PIN  = GPIO 12    # Reset pin
DC_PIN   = GPIO 8     # Data/Command selection
CS_PIN   = GPIO 9     # Chip Select
BUSY_PIN = GPIO 13    # Busy state indicator
MOSI     = GPIO 11    # SPI1 MOSI
SCK      = GPIO 10    # SPI1 Clock
```

## External references

- [Waveshare Pico-ePaper-2.13 Wiki](https://www.waveshare.com/wiki/Pico-ePaper-2.13)
- [waveshare/Pico_ePaper_Code](https://github.com/waveshare/Pico_ePaper_Code)
