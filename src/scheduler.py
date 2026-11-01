"""
Task scheduler for HAUKI - Raspberry Pi implementation
"""
import time

MINUTE_INTERVAL = 60
# Wake this long after each full minute, so a slot that starts on the minute has begun
WAKE_OFFSET = 1


def sleep_until_next_minute():
    # Slot boundaries always fall on a full minute, so waking just after each one
    # shows a new price within seconds of it starting
    time.sleep(MINUTE_INTERVAL - time.time() % MINUTE_INTERVAL + WAKE_OFFSET)


class TaskScheduler:
    def __init__(self, display, health_checker, prices):
        self.display = display
        self.health = health_checker
        self.prices = prices

        # 0 is the sentinel for "no valid slot yet"
        self.last_slot = 0

    def minute_task(self):
        current_slot = self.prices.current_slot
        if current_slot == self.last_slot:
            return
        current_price = self.prices.get_metering_price()
        if current_price is not None:
            self.last_slot = current_slot
            # When the meter bills longer periods than prices change, the big number is
            # the period average and the slot price is shown small next to it
            slot_price = None
            if self.prices.metering_interval != self.prices.slot_duration:
                slot_price = self.prices.get_current_price()
            self.display.show_price(
                current_price,
                self.prices.unit,
                [self.prices.get_box(item) for item in self.display.box_items],
                slot_price,
            )

    def run(self):
        """Main scheduler loop. Does not return under normal operation."""
        # run() is entered at startup and again after every error screen; forgetting
        # the shown slot makes the price replace the error as soon as checks pass
        self.last_slot = 0
        while True:
            self.health.check()
            self.minute_task()
            sleep_until_next_minute()
