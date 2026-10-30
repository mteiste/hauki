"""
E-ink display driver for HAUKI - Raspberry Pi 1A+ implementation
Waveshare 2.13" V4 HAT: layout drawn with Pillow, sent through epd.py
"""
from PIL import Image, ImageDraw, ImageFont

from epd import EPD, HEIGHT, WIDTH, image_to_buffer

FONT_PATH_DEFAULT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


class Display:
    """Display manager for Waveshare 2.13" V4 e-ink display."""

    def __init__(self, config, epd=None):
        """Args:
            config: Config object
            epd: Object with display(buffer); defaults to the real panel. The PNG
                preview passes its own so the same layout code runs without hardware.
        """
        cfg = config.display_settings()
        if epd is None:
            epd = EPD(
                rst_pin=cfg.get('rst_pin', 17),
                dc_pin=cfg.get('dc_pin', 25),
                busy_pin=cfg.get('busy_pin', 24),
            )
            epd.init()
        self.epd = epd
        font_path = cfg.get('font_path', FONT_PATH_DEFAULT)
        self.font48 = ImageFont.truetype(font_path, 48)
        self.font32 = ImageFont.truetype(font_path, 32)
        self.font30 = ImageFont.truetype(font_path, 30)
        self.font14 = ImageFont.truetype(font_path, 14)
        self.font12 = ImageFont.truetype(font_path, 12)

    def _new_image(self):
        return Image.new('1', (WIDTH, HEIGHT), 255)

    def show_price(self, current_price, unit, cheapest_1h, cheapest_2h, cheapest_4h):
        image = self._new_image()
        draw = ImageDraw.Draw(image)

        # Positioned by baseline ('ls'/'rs' anchors). Font sizes are the largest that
        # fit the widest value, 999.99 c/kWh: 168 + unit 43 px, 241 px and 246 px wide
        draw.text((0, 40), f"{current_price:.2f}", font=self.font48, fill=0, anchor='ls')
        draw.text((WIDTH - 1, 40), unit, font=self.font14, fill=0, anchor='rs')

        time_str, avg_price = cheapest_1h
        draw.text((0, 80), f"{avg_price:.2f} @ {time_str}", font=self.font30, fill=0, anchor='ls')

        time_str_2h, avg_price_2h = cheapest_2h
        time_str_4h, avg_price_4h = cheapest_4h
        draw.text(
            (0, 117),
            f"2h: {avg_price_2h:.2f} @ {time_str_2h}  4h: {avg_price_4h:.2f} @ {time_str_4h}",
            font=self.font12,
            fill=0,
            anchor='ls',
        )

        self.epd.display(image_to_buffer(image))

    def show_error(self, message, details=""):
        image = self._new_image()
        draw = ImageDraw.Draw(image)

        draw.text((0, 0), "ERROR", font=self.font32, fill=0)
        draw.text((0, 40), message, font=self.font14, fill=0)
        if details:
            draw.text((0, 60), details, font=self.font12, fill=0)

        self.epd.display(image_to_buffer(image))

    def show_status(self, message):
        image = self._new_image()
        draw = ImageDraw.Draw(image)

        draw.text((0, 50), message, font=self.font14, fill=0)

        self.epd.display(image_to_buffer(image))
