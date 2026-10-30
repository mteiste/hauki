"""
Entry point for HAUKI - Raspberry Pi 1A+ implementation
"""
import sys
import time
import traceback

from config import Config
from eink import Display
from exceptions import HaukiError
from healthcheck import HealthChecker
from homeassistant import HomeAssistant
from prices import Prices
from scheduler import TaskScheduler

if __name__ == "__main__":
    config = Config()
    display = Display(config)
    ha = HomeAssistant(config)
    prices = Prices(ha, config)
    health = HealthChecker(ha, prices)
    scheduler = TaskScheduler(display, health, prices)

    display.show_status("Starting...")

    while True:
        try:
            scheduler.run()
        except KeyboardInterrupt:
            display.show_status("Stopped")
            sys.exit(0)
        except HaukiError as e:
            traceback.print_exc()
            display.show_error(e.message, e.detail)
            time.sleep(60)
        except Exception as e:
            traceback.print_exc()
            display.show_error("Unexpected error", str(e))
            time.sleep(60)
