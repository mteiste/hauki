#!/usr/bin/env python3
"""
Display test tool for HAUKI - Raspberry Pi implementation

Drives the Waveshare 2.13" V4 HAT through the same epd.py / eink.py code the
service uses, in stages, so a failure points at one layer:

    handshake  reset + SWRESET, report BUSY behaviour (no visible change)
    clear      full refresh to white
    geometry   border, corner labels and an "up" arrow: rotation, mirroring, padding
    layout     the real show_price / show_error / show_status screens with sample data
    sleep      put the controller into deep sleep

With --png the panel is replaced by a preview that decodes each RAM buffer back
to an image and saves it, so layout work needs no Pi. Hardware-only stages
(handshake, clear, sleep) are skipped in that mode.

Usage (from rpi/):
    python3 tools/display_test.py                       # all stages on the Pi
    python3 tools/display_test.py geometry layout       # selected stages
    .venv/bin/python tools/display_test.py --png preview    # workstation preview
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from config import Config  # noqa: E402
from eink import FONT_PATH_DEFAULT, Display  # noqa: E402
from epd import (  # noqa: E402
    BUFFER_SIZE,
    EPD,
    HEIGHT,
    WIDTH,
    buffer_to_image,
    image_to_buffer,
)

STAGES = ['handshake', 'clear', 'geometry', 'layout', 'sleep']
HARDWARE_ONLY = {'handshake', 'clear', 'sleep'}
PREVIEW_SCALE = 4

# (name, method, args) shown in the layout stage. The "wide" case is the widest the
# layout is sized for: every price just under 10 EUR/kWh (999.99 c/kWh).
LAYOUT_SAMPLES = [
    ('price', 'show_price', (12.34, 'c/kWh', ('03:15', 2.15), ('02:45', 2.48), ('01:30', 3.07))),
    ('price-wide', 'show_price', (999.99, 'c/kWh', ('23:45', 999.99), ('23:45', 999.99), ('23:45', 999.99))),
    ('error', 'show_error', ('Could not fetch prices', 'HA entity error')),
    ('status', 'show_status', ('Starting...',)),
]


class PngPanel:
    """Stands in for EPD: decodes each RAM buffer and saves it as PNG."""

    def __init__(self, outdir):
        self.outdir = Path(outdir)
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.name = 'screen'

    def display(self, buffer):
        if len(buffer) != BUFFER_SIZE:
            raise ValueError(f"buffer is {len(buffer)} bytes, expected {BUFFER_SIZE}")
        image = buffer_to_image(buffer)
        path = self.outdir / f'{self.name}.png'
        image.save(path)
        image.resize((WIDTH * PREVIEW_SCALE, HEIGHT * PREVIEW_SCALE), Image.NEAREST).save(
            self.outdir / f'{self.name}@{PREVIEW_SCALE}x.png'
        )
        print(f"  wrote {path}")


def geometry_image(font_path):
    image = Image.new('1', (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, 14)

    # Outermost pixel rows/columns: any lost edge shows as a missing border line
    draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=0)
    draw.text((3, 2), 'TL', font=font, fill=0)
    draw.text((WIDTH - 4, 2), 'TR', font=font, fill=0, anchor='ra')
    draw.text((3, HEIGHT - 3), 'BL', font=font, fill=0, anchor='ld')
    draw.text((WIDTH - 4, HEIGHT - 3), 'BR', font=font, fill=0, anchor='rd')

    cx, cy = WIDTH // 2, HEIGHT // 2
    draw.polygon([(cx, 20), (cx - 15, 45), (cx + 15, 45)], fill=0)
    draw.rectangle((cx - 4, 45, cx + 4, 80), fill=0)
    draw.text((cx, cy + 30), f'UP  {WIDTH}x{HEIGHT}', font=font, fill=0, anchor='mm')
    return image


def check_conversion(image):
    """The RAM buffer must decode back to the same pixels."""
    buffer = image_to_buffer(image)
    if len(buffer) != BUFFER_SIZE:
        raise ValueError(f"buffer is {len(buffer)} bytes, expected {BUFFER_SIZE}")
    if buffer_to_image(buffer).tobytes() != image.tobytes():
        raise ValueError("buffer round trip changed the image")
    print(f"  buffer conversion OK ({BUFFER_SIZE} bytes)")


def run_handshake(epd):
    epd.reset()
    after_reset = epd.wait_busy()
    epd.send_command(0x12)  # SWRESET
    went_busy = epd.is_busy()
    swreset = epd.wait_busy()
    print(f"  BUSY low {after_reset:.3f} s after reset; SWRESET took {swreset:.3f} s")
    if not went_busy:
        print("  Warning: BUSY never went high after SWRESET - is the HAT seated?")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('stages', nargs='*', metavar='STAGE',
                        help=f"stages to run, any of: {' '.join(STAGES)} (default: all)")
    parser.add_argument('--png', metavar='DIR', help='write PNG previews to DIR instead of the panel')
    parser.add_argument('--pause', type=float, default=5.0,
                        help='seconds to show each screen on the panel (default: 5)')
    args = parser.parse_args()
    unknown = set(args.stages) - set(STAGES)
    if unknown:
        parser.error(f"unknown stage(s): {' '.join(sorted(unknown))}")
    # Always run in the fixed order; handshake before init, sleep last
    stages = [s for s in STAGES if s in args.stages] if args.stages else STAGES

    config = Config()
    font_path = config.display_settings().get('font_path', FONT_PATH_DEFAULT)

    if args.png:
        panel = PngPanel(args.png)
        epd = None
        display = Display(config, epd=panel)
        for stage in [s for s in stages if s in HARDWARE_ONLY]:
            print(f"[{stage}] skipped: needs the panel")
    else:
        cfg = config.display_settings()
        epd = EPD(rst_pin=cfg.get('rst_pin', 17), dc_pin=cfg.get('dc_pin', 25),
                  busy_pin=cfg.get('busy_pin', 24))
        panel = epd

    try:
        if epd is not None:
            if 'handshake' in stages:
                print("[handshake]")
                run_handshake(epd)
            epd.init()
            display = Display(config, epd=epd)

        if 'clear' in stages and epd is not None:
            print("[clear]")
            print(f"  full refresh {epd.clear():.2f} s")

        if 'geometry' in stages:
            print("[geometry]")
            image = geometry_image(font_path)
            check_conversion(image)
            panel.name = 'geometry'
            start = time.monotonic()
            panel.display(image_to_buffer(image))
            if epd is not None:
                print(f"  shown in {time.monotonic() - start:.2f} s - check the border and that UP points up")
                time.sleep(args.pause)

        if 'layout' in stages:
            print("[layout]")
            for name, method, sample in LAYOUT_SAMPLES:
                panel.name = name
                start = time.monotonic()
                getattr(display, method)(*sample)
                if epd is not None:
                    print(f"  {name}: shown in {time.monotonic() - start:.2f} s")
                    time.sleep(args.pause)

        if 'sleep' in stages and epd is not None:
            print("[sleep]")
            epd.sleep()
    finally:
        if epd is not None:
            epd.close()


if __name__ == '__main__':
    main()
