# *****************************************************************************
# * | File        :   eink.py
# * | Project     :   HAUKI - Home Assistant Update Kiosk Interface
# * | Info        :   E-Paper display driver for Waveshare 2.13" V4
# *----------------
# * | Derived from:   Pico_ePaper-2.13_V4.py
# * | Original Author: Waveshare team
# * | Fork Date   :   2026-03-09
# * | Changes     :   Refactored for HAUKI project, removed debug prints,
# *                   fixed typos, removed demo code
# -----------------------------------------------------------------------------
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import fonts.font12 as font12
import fonts.font14 as font14
import fonts.font32 as font32
import fonts.font48 as font48
import framebuf
import utime
from machine import SPI, Pin

from lib.writer import Writer

EPD_WIDTH = 122
EPD_HEIGHT = 250

RST_PIN = 12
DC_PIN = 8
CS_PIN = 9
BUSY_PIN = 13


class EPD_Landscape(framebuf.FrameBuffer):
    """Landscape orientation (250x122) e-Paper display driver for Waveshare 2.13" V4"""

    # Display update control modes
    UPDATE_FULL = 0xf7  # Full refresh with complete waveform
    UPDATE_FAST = 0xC7  # Fast refresh with abbreviated waveform

    # Full refresh every N fast refreshes to clear ghosting; 10 is empirically
    # determined for this display model before ghosting becomes visible
    REFRESH_THRESHOLD = 10

    def __init__(self):
        self.reset_pin = Pin(RST_PIN, Pin.OUT)
        self.busy_pin = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)
        self.cs_pin = Pin(CS_PIN, Pin.OUT)

        # Physical display dimensions (portrait hardware)
        if EPD_WIDTH % 8 == 0:
            self._physical_width = EPD_WIDTH
        else:
            self._physical_width = (EPD_WIDTH // 8) * 8 + 8
        self._physical_height = EPD_HEIGHT

        self.spi = SPI(1)
        self.spi.init(baudrate=4000_000)  # type: ignore
        self.dc_pin = Pin(DC_PIN, Pin.OUT)

        # Buffers use physical dimensions (both must be same size for transformation)
        buffer_size = self._physical_height * self._physical_width // 8
        self.buffer = bytearray(buffer_size)
        self._reordered_buffer = bytearray(buffer_size)

        # Refresh tracking for smart display mode
        self._refresh_counter = self.REFRESH_THRESHOLD  # Trigger full refresh on first display()

        # Set landscape dimensions for Writer library (swapped from physical portrait)
        self.width = self._physical_height
        self.height = self._physical_width

        # Initialize FrameBuffer in landscape orientation
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)

        # Initialize display controller
        self._reset()
        self._delay_ms(100)

        self._read_busy()
        self._send_command(0x12)  # SWRESET
        self._read_busy()

        self._send_command(0x01)  # Driver output control
        self._send_data(0xf9)
        self._send_data(0x00)
        self._send_data(0x00)

        self._send_command(0x11)  # data entry mode
        self._send_data(0x07)

        self._set_windows(0, 0, self._physical_width - 1, self._physical_height - 1)
        self._set_cursor(0, 0)

        self._send_command(0x3C)  # BorderWaveform
        self._send_data(0x05)

        self._send_command(0x21)  # Display update control
        self._send_data(0x00)
        self._send_data(0x80)

        self._send_command(0x18)  # Read built-in temperature sensor
        self._send_data(0x80)

        self._read_busy()

    def _digital_write(self, pin, value):
        pin.value(value)

    def _digital_read(self, pin):
        return pin.value()

    def _delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def _spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def _reset(self):
        self._digital_write(self.reset_pin, 1)
        self._delay_ms(20)
        self._digital_write(self.reset_pin, 0)
        self._delay_ms(2)
        self._digital_write(self.reset_pin, 1)
        self._delay_ms(20)

    def _send_command(self, command):
        self._digital_write(self.dc_pin, 0)
        self._digital_write(self.cs_pin, 0)
        self._spi_writebyte([command])
        self._digital_write(self.cs_pin, 1)

    def _send_data(self, data):
        self._digital_write(self.dc_pin, 1)
        self._digital_write(self.cs_pin, 0)
        self._spi_writebyte([data])
        self._digital_write(self.cs_pin, 1)

    def _send_data1(self, buf):
        self._digital_write(self.dc_pin, 1)
        self._digital_write(self.cs_pin, 0)
        self.spi.write(bytearray(buf))
        self._digital_write(self.cs_pin, 1)

    def _read_busy(self):
        self._delay_ms(10)
        while (self._digital_read(self.busy_pin) == 1):
            self._delay_ms(10)

    def _turn_on_display(self, mode):
        self._send_command(0x22)  # Display Update Control
        self._send_data(mode)
        self._send_command(0x20)  # Activate Display Update Sequence
        self._read_busy()

    def _set_windows(self, Xstart, Ystart, Xend, Yend):
        self._send_command(0x44)                # SET_RAM_X_ADDRESS_START_END_POSITION
        self._send_data((Xstart >> 3) & 0xFF)
        self._send_data((Xend >> 3) & 0xFF)

        self._send_command(0x45)                # SET_RAM_Y_ADDRESS_START_END_POSITION
        self._send_data(Ystart & 0xFF)
        self._send_data((Ystart >> 8) & 0xFF)
        self._send_data(Yend & 0xFF)
        self._send_data((Yend >> 8) & 0xFF)

    def _set_cursor(self, Xstart, Ystart):
        self._send_command(0x4E)             # SET_RAM_X_ADDRESS_COUNTER
        self._send_data(Xstart & 0xFF)

        self._send_command(0x4F)             # SET_RAM_Y_ADDRESS_COUNTER
        self._send_data(Ystart & 0xFF)
        self._send_data((Ystart >> 8) & 0xFF)

    def clear(self):
        """Clear framebuffer to white."""
        self.buffer[:] = b'\xff' * len(self.buffer)
        self._refresh_counter = self.REFRESH_THRESHOLD

    def _display(self, image, mode):
        """Internal: Send image to display with specified refresh mode."""
        self._send_command(0x24)
        self._send_display_buffer(image)
        self._turn_on_display(mode)

    def display(self, image):
        """Update display with automatic refresh mode selection.

        Smart selection based on refresh history:
        - First call: full refresh for clean start (~2s)
        - Subsequent calls: fast refresh for speed (~1s)
        - Periodic: full refresh every N calls to eliminate ghosting (~2s)
        """
        if self._refresh_counter >= self.REFRESH_THRESHOLD:
            self._display(image, self.UPDATE_FULL)
            self._refresh_counter = 0
        else:
            self._display(image, self.UPDATE_FAST)
            self._refresh_counter += 1

    def _display_base(self, image):
        self._send_command(0x24)
        self._send_display_buffer(image)

        self._send_command(0x26)
        self._send_display_buffer(image)

        self._turn_on_display(self.UPDATE_FULL)
        self._refresh_counter = 0

    def _sleep(self):
        self._send_command(0x10)  # enter deep sleep
        self._send_data(0x01)
        self._delay_ms(100)

    def _send_display_buffer(self, image):
        """Send display buffer for landscape orientation with pixel reordering

        Transforms logical landscape buffer (250x122) to physical portrait display (122x250).
        MONO_VLSB packs pixels vertically (each byte is a column of 8 pixels), so the
        landscape buffer must be transposed column-by-column to match the hardware's
        horizontal scan order.
        """
        idx = 0
        width_bytes = int(self._physical_width / 8)
        for j in range(width_bytes - 1, -1, -1):
            for i in range(0, self._physical_height):
                self._reordered_buffer[idx] = image[i + j * self._physical_height]
                idx += 1

        self._send_data1(self._reordered_buffer)
        self._delay_ms(100)


class PriceDisplay:
    """High-level display manager for showing electricity price information."""

    def __init__(self, epd):
        """Initialize display manager.

        Args:
            epd: EPD_Landscape instance
        """
        self.epd = epd
        self.wri48 = Writer(epd, font48)
        self.wri32 = Writer(epd, font32)
        self.wri14 = Writer(epd, font14)
        self.wri12 = Writer(epd, font12)

    def show_price(self, current_price, unit, cheapest_1h, cheapest_2h, cheapest_4h):
        """Show main price display with current price and cheapest windows.

        Args:
            current_price: Current electricity price (float)
            unit: Price unit string (e.g., "¢/kWh")
            cheapest_1h: Tuple of (time_string, avg_price) for 1h window
            cheapest_2h: Tuple of (time_string, avg_price) for 2h window
            cheapest_4h: Tuple of (time_string, avg_price) for 4h window
        """
        self.epd.clear()

        Writer.set_textpos(self.epd, 5, 0)
        self.wri48.printstring(f"{current_price:.2f}", invert=True)

        Writer.set_textpos(self.epd, 107, 211)
        self.wri14.printstring(unit, invert=True)

        time_str, avg_price = cheapest_1h
        Writer.set_textpos(self.epd, 70, 0)
        self.wri32.printstring(f"{avg_price:.2f} @ {time_str}", invert=True)

        time_str_2h, avg_price_2h = cheapest_2h
        time_str_4h, avg_price_4h = cheapest_4h
        Writer.set_textpos(self.epd, 105, 0)
        self.wri12.printstring(f"2h: {avg_price_2h:.2f} @ {time_str_2h}  4h: {avg_price_4h:.2f} @ {time_str_4h}", invert=True)

        self.epd.display(self.epd.buffer)

    def show_error(self, message, details=""):
        """Show error message prominently.

        Args:
            message: Short error message string
            details: Optional additional details
        """
        self.epd.clear()

        Writer.set_textpos(self.epd, 0, 0)
        self.wri32.printstring("ERROR", invert=True)

        Writer.set_textpos(self.epd, 40, 0)
        self.wri14.printstring(message, invert=True)

        if details:
            Writer.set_textpos(self.epd, 60, 0)
            self.wri12.printstring(details, invert=True)

        self.epd.display(self.epd.buffer)

    def show_status(self, message):
        """Show status message during boot/initialization.

        Args:
            message: Status message to display
        """
        self.epd.clear()

        Writer.set_textpos(self.epd, 50, 0)
        self.wri14.printstring(message, invert=True)

        self.epd.display(self.epd.buffer)
