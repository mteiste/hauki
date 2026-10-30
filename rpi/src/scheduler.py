"""
Task scheduler for HAUKI - Raspberry Pi implementation
"""
import time

MINUTE_INTERVAL = 60


class TaskScheduler:
    def __init__(self, display, health_checker, prices):
        self.display = display
        self.health = health_checker
        self.prices = prices

        self.cheapest_1h = None
        self.cheapest_2h = None
        self.cheapest_4h = None
        # 0 is the sentinel for "no valid slot yet"
        self.last_slot = 0
        self.last_minute_task = 0

    def minute_task(self):
        current_slot = self.prices.current_slot
        if current_slot == self.last_slot:
            return
        self.cheapest_1h = self.prices.find_cheapest_window(1)
        self.cheapest_2h = self.prices.find_cheapest_window(2)
        self.cheapest_4h = self.prices.find_cheapest_window(4)
        current_price = self.prices.get_current_price()
        if current_price is not None:
            self.last_slot = current_slot
            self.display.show_price(
                current_price,
                self.prices.unit,
                self.cheapest_1h,
                self.cheapest_2h,
                self.cheapest_4h,
            )

    def run(self):
        """Main scheduler loop. Does not return under normal operation."""
        while True:
            self.health.check()

            current_time = time.time()

            if current_time - self.last_minute_task >= MINUTE_INTERVAL:
                self.minute_task()
                self.last_minute_task = current_time

            current_time = time.time()
            time_until_next = MINUTE_INTERVAL - (current_time - self.last_minute_task)
            if time_until_next <= 0:
                time_until_next = MINUTE_INTERVAL
            time.sleep(time_until_next)
