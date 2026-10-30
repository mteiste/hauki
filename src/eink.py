"""
E-ink display driver for HAUKI - Raspberry Pi 1A+ implementation
Waveshare 2.13" V4 HAT: layout drawn with Pillow, sent through epd.py
"""
import time

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
        # The header shows the current slot, so it uses the same slot length as prices
        self.slot_duration = config.price_settings().get('slot_duration', 900)
        font_path = cfg.get('font_path', FONT_PATH_DEFAULT)
        self.font42 = ImageFont.truetype(font_path, 42)
        self.font28 = ImageFont.truetype(font_path, 28)
        self.font21 = ImageFont.truetype(font_path, 21)
        self.font14 = ImageFont.truetype(font_path, 14)
        self.font13 = ImageFont.truetype(font_path, 13)
        self.font12 = ImageFont.truetype(font_path, 12)

    def _new_image(self, unit=None):
        """New white image with the header drawn; returns (image, draw).

        Every update shows the date and the current slot, so a frozen e-paper image
        (the panel keeps it without power) is easy to tell apart from a running system.
        """
        image = Image.new('1', (WIDTH, HEIGHT), 255)
        draw = ImageDraw.Draw(image)

        now = time.time()
        slot_start = now - now % self.slot_duration
        start = time.localtime(slot_start)
        end = time.localtime(slot_start + self.slot_duration)
        draw.text((0, 12), time.strftime('%d.%m.%Y', start), font=self.font13, fill=0, anchor='ls')
        if unit:
            draw.text((WIDTH // 2, 12), unit, font=self.font13, fill=0, anchor='ms')
        # The slot sits top right, directly above the slot price shown by show_price
        slot = f"{time.strftime('%H:%M', start)}–{time.strftime('%H:%M', end)}"
        draw.text((WIDTH - 1, 12), slot, font=self.font13, fill=0, anchor='rs')
        draw.line((0, 16, WIDTH - 1, 16), fill=0)
        return image, draw

    def show_price(self, current_price, unit, cheapest_1h, cheapest_2h, cheapest_4h,
                   slot_price=None):
        """Args:
            current_price: Price billed for the current metering period
            slot_price: Current slot price, only when it differs in meaning from
                current_price (metering period longer than the price slot)
        """
        image, draw = self._new_image(unit)

        # Positioned by baseline. Prices are always the largest text, so the most
        # visible number is never something else. Sizes fit the widest value,
        # 999.99 c/kWh: 147 px for the current price, 73 px in an 80 px box.
        # The current price is centred between the header rule (y=16) and the boxes (y=85).
        draw.text((WIDTH // 2, 66), f"{current_price:.2f}", font=self.font42, fill=0, anchor='ms')
        if slot_price is not None:
            draw.text((WIDTH - 1, 30), f"{slot_price:.2f}", font=self.font13, fill=0, anchor='rs')

        windows = (('1h', cheapest_1h), ('2h', cheapest_2h), ('4h', cheapest_4h))
        for i, (label, (time_str, avg_price)) in enumerate(windows):
            # Three 82 px boxes with 2 px gaps fill the 250 px width
            left = i * 84
            right = left + 81
            draw.rectangle((left, 85, right, HEIGHT - 1), outline=0)
            draw.text((left + 3, 98), label, font=self.font13, fill=0, anchor='ls')
            draw.text((right - 3, 98), time_str, font=self.font13, fill=0, anchor='rs')
            draw.text(((left + right) // 2, 118), f"{avg_price:.2f}", font=self.font21, fill=0, anchor='ms')

        self.epd.display(image_to_buffer(image))

    def show_error(self, message, details=""):
        image, draw = self._new_image()

        draw.text((WIDTH // 2, 52), "ERROR", font=self.font28, fill=0, anchor='ms')
        draw.text((0, 76), message, font=self.font14, fill=0, anchor='ls')
        if details:
            draw.text((0, 96), details, font=self.font12, fill=0, anchor='ls')

        self.epd.display(image_to_buffer(image))

    def show_status(self, message):
        image, draw = self._new_image()

        draw.text((0, 72), message, font=self.font14, fill=0, anchor='ls')

        self.epd.display(image_to_buffer(image))
