"""
Low-level driver for the Waveshare 2.13" V4 e-paper HAT (SSD1680 controller)
SPI via spidev (kernel driver owns CS/CE0); RST, DC and BUSY via lgpio

Command sequence derived from Waveshare's epd2in13_V4.py (see LICENSES/WAVESHARE).
"""
import time

from PIL import Image

# Panel geometry in the controller's native portrait orientation
PANEL_WIDTH = 122
PANEL_HEIGHT = 250
# RAM rows are byte-aligned: 122 px padded to 16 bytes
ROW_BYTES = (PANEL_WIDTH + 7) // 8
BUFFER_SIZE = ROW_BYTES * PANEL_HEIGHT

# Application code draws in landscape
WIDTH = PANEL_HEIGHT
HEIGHT = PANEL_WIDTH

UPDATE_FULL = 0xF7
UPDATE_FAST = 0xC7

BUSY_TIMEOUT = 10


def image_to_buffer(image):
    """Convert a landscape WIDTH x HEIGHT image to controller RAM bytes."""
    # Rotating 90 degrees counter-clockwise matches Waveshare's RPi driver for the HAT
    portrait = image.convert('1').rotate(90, expand=True)
    # Mode '1' packs rows MSB-first, padded to whole bytes, which is the RAM layout
    # for data entry mode 0x03; 1 = white in both
    return portrait.tobytes('raw')


def buffer_to_image(buffer):
    """Inverse of image_to_buffer, for checking the conversion without hardware."""
    portrait = Image.frombytes('1', (PANEL_WIDTH, PANEL_HEIGHT), bytes(buffer))
    return portrait.rotate(-90, expand=True)


class EPD:
    """Waveshare 2.13" V4 panel on SPI0 CE0 and gpiochip0."""

    # Full refresh every N fast refreshes to clear ghosting; 10 is an empirical value
    # for this panel
    REFRESH_THRESHOLD = 10

    def __init__(self, rst_pin, dc_pin, busy_pin, spi_speed_hz=4_000_000):
        # Imported here because lgpio creates a notification pipe in $LG_WD (or the
        # working directory) on import; the PNG preview must not need these at all
        import lgpio
        import spidev

        self._lgpio = lgpio
        self.rst_pin = rst_pin
        self.dc_pin = dc_pin
        self.busy_pin = busy_pin

        self._chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self._chip, rst_pin, 1)
        lgpio.gpio_claim_output(self._chip, dc_pin, 0)
        lgpio.gpio_claim_input(self._chip, busy_pin)

        self._spi = spidev.SpiDev()
        self._spi.open(0, 0)
        self._spi.max_speed_hz = spi_speed_hz
        self._spi.mode = 0

        self._refresh_counter = self.REFRESH_THRESHOLD
        self._fast_waveform_loaded = False

    def close(self):
        self._spi.close()
        self._lgpio.gpiochip_close(self._chip)

    def is_busy(self):
        return self._lgpio.gpio_read(self._chip, self.busy_pin) == 1

    def wait_busy(self):
        """Wait for BUSY to go low. Returns the wait in seconds."""
        start = time.monotonic()
        while self.is_busy():
            if time.monotonic() - start > BUSY_TIMEOUT:
                raise TimeoutError(f"e-paper BUSY still high after {BUSY_TIMEOUT} s")
            time.sleep(0.01)
        return time.monotonic() - start

    def reset(self):
        self._lgpio.gpio_write(self._chip, self.rst_pin, 1)
        time.sleep(0.02)
        self._lgpio.gpio_write(self._chip, self.rst_pin, 0)
        time.sleep(0.002)
        self._lgpio.gpio_write(self._chip, self.rst_pin, 1)
        time.sleep(0.02)

    def send_command(self, command):
        self._lgpio.gpio_write(self._chip, self.dc_pin, 0)
        self._spi.writebytes([command])

    def send_data(self, data):
        self._lgpio.gpio_write(self._chip, self.dc_pin, 1)
        # writebytes2 splits transfers larger than the spidev buffer (4096 bytes)
        self._spi.writebytes2(bytes(data))

    def init(self):
        """Reset the controller and configure it for full-panel landscape updates."""
        self.reset()
        self.wait_busy()
        self.send_command(0x12)  # SWRESET
        self.wait_busy()

        self.send_command(0x01)  # Driver output control: 250 gate lines
        self.send_data([0xF9, 0x00, 0x00])

        self.send_command(0x11)  # Data entry mode: X then Y increment, X-major
        self.send_data([0x03])

        self.send_command(0x44)  # RAM X window, in bytes
        self.send_data([0x00, (PANEL_WIDTH - 1) >> 3])
        self.send_command(0x45)  # RAM Y window
        self.send_data([0x00, 0x00, (PANEL_HEIGHT - 1) & 0xFF, (PANEL_HEIGHT - 1) >> 8])

        self.send_command(0x4E)  # RAM X counter
        self.send_data([0x00])
        self.send_command(0x4F)  # RAM Y counter
        self.send_data([0x00, 0x00])

        self.send_command(0x3C)  # Border waveform
        self.send_data([0x05])

        self.send_command(0x21)  # Display update control
        self.send_data([0x00, 0x80])

        self.send_command(0x18)  # Use the built-in temperature sensor
        self.send_data([0x80])

        self.wait_busy()
        # Panel content is unknown after reset, so the next update must be full
        self._refresh_counter = self.REFRESH_THRESHOLD
        self._fast_waveform_loaded = False

    def _refresh(self, mode):
        self.send_command(0x22)  # Display update control 2
        self.send_data([mode])
        self.send_command(0x20)  # Activate display update sequence
        return self.wait_busy()

    def _load_fast_waveform(self):
        # The OTP waveform is picked by temperature; a fake 100 C selects the fast
        # one. A full refresh (0xF7) reads the real sensor and loads the normal
        # waveform again, so this has to be repeated after every full refresh.
        self.send_command(0x1A)  # Write temperature register
        self.send_data([0x64, 0x00])
        self.send_command(0x22)
        self.send_data([0x91])  # Load waveform for the written temperature
        self.send_command(0x20)
        self.wait_busy()
        self._fast_waveform_loaded = True

    def display(self, buffer):
        """Write a RAM buffer and refresh, full every REFRESH_THRESHOLD updates.

        Returns the refresh time in seconds.
        """
        self.send_command(0x24)  # Write black/white RAM
        self.send_data(buffer)

        if self._refresh_counter >= self.REFRESH_THRESHOLD:
            self._refresh_counter = 0
            self._fast_waveform_loaded = False
            return self._refresh(UPDATE_FULL)
        self._refresh_counter += 1
        if not self._fast_waveform_loaded:
            self._load_fast_waveform()
        # 0xC7 refreshes with the waveform already loaded
        return self._refresh(UPDATE_FAST)

    def clear(self):
        """Full refresh to white."""
        self._refresh_counter = self.REFRESH_THRESHOLD
        return self.display(b'\xff' * BUFFER_SIZE)

    def sleep(self):
        """Enter deep sleep; only a reset (init) wakes the controller."""
        self.send_command(0x10)
        self.send_data([0x01])
        time.sleep(0.1)
