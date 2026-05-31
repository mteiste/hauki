"""
Main entry point for Raspberry Pi Pico project
HAUKI - Home Assistant Update Kiosk Interface
"""
import sys
import time

from config import Config
from eink import EPD_Landscape, PriceDisplay
from exceptions import HaukiError, RtcSyncError
from healthcheck import HealthChecker
from homeassistant import HomeAssistant
from nordpool import NordPool
from scheduler import TaskScheduler
from timezone import LocalTimezone
from wifi import WiFi


def connect_wifi(wifi, display):
    """Attempt a single WiFi connection.

    Args:
        wifi: WiFi object
        display: PriceDisplay object
    """
    display.show_status("Connecting WiFi...")
    wifi.connect()


def sync_clock(wifi, display):
    """Sync RTC with NTP server.

    Args:
        wifi: WiFi object
        display: PriceDisplay object
    """
    display.show_status("Syncing clock...")
    if not wifi.sync_rtc():
        raise RtcSyncError()


if __name__ == "__main__":
    config = Config()
    clock = LocalTimezone(config)

    epd = EPD_Landscape()
    display = PriceDisplay(epd)

    wifi = WiFi(config)
    ha = HomeAssistant(config)

    # Constructed once before the loop to avoid reallocation on each retry
    nordpool = NordPool(ha, clock, config)
    health = HealthChecker(wifi, ha, nordpool)
    scheduler = TaskScheduler(display, health, nordpool, wifi, clock)

    display.show_status("Starting...")

    while True:
        try:
            connect_wifi(wifi, display)
            # Clock must be synced before entering scheduler — slot calculations
            # depend on accurate UTC time and will return slot 0 (no data) if the
            # RTC is still at the MicroPython epoch default (2021-01-01)
            sync_clock(wifi, display)
            scheduler.run()
        except KeyboardInterrupt:
            display.show_status("Stopped")
            break
        except HaukiError as e:
            sys.print_exception(e)  # type: ignore
            display.show_error(e.message, e.detail)
            # Keep error visible long enough to read; also avoids hammering HA on persistent failures
            time.sleep(60)
        except Exception as e:
            sys.print_exception(e)  # type: ignore
            display.show_error("Unexpected error", str(e))
            time.sleep(60)
