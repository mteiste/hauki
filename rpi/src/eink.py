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
