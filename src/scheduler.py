"""
Task scheduler for HAUKI
Simple interval-based task execution
"""
import time

from exceptions import RtcSyncError

MINUTE_INTERVAL = 60
SIX_HOUR_INTERVAL = 6 * 60 * 60


class TaskScheduler:
    """Simple task scheduler with fixed intervals

    Runs tasks at different intervals:
    - Every minute
    - Four times per day (every 6 hours)
    """

    def __init__(self, display, health_checker, nordpool, wifi, clock):
        """Initialize scheduler with components

        Args:
            display: PriceDisplay object
            health_checker: HealthChecker object
            nordpool: NordPool object
            wifi: WiFi object
            clock: LocalTimezone object for UTC timestamps
        """
        self.display = display
        self.health = health_checker
        self.nordpool = nordpool
        self.wifi = wifi
        self.clock = clock

        self.cheapest_1h = None
        self.cheapest_2h = None
        self.cheapest_4h = None
        # 0 is the sentinel for "no valid slot yet", so the first tick always attempts a display update
        self.last_slot = 0

        self.last_minute_task = 0
        self.last_six_hour_task = 0

    def minute_task(self):
        """Task executed every minute"""
        current_slot = self.nordpool.current_slot
        if current_slot == self.last_slot:
            return
        self.cheapest_1h = self.nordpool.find_cheapest_window(1)
        self.cheapest_2h = self.nordpool.find_cheapest_window(2)
        self.cheapest_4h = self.nordpool.find_cheapest_window(4)
        current_price = self.nordpool.get_current_price()
        if current_price is not None:
            # Only advance last_slot on success — if price is None the data isn't
            # ready yet, and we want to retry on the next tick rather than skip the slot
            self.last_slot = current_slot
            self.display.show_price(
                current_price,
                self.nordpool.unit,
                self.cheapest_1h,
                self.cheapest_2h,
                self.cheapest_4h
            )

    def six_hour_task(self):
        """Task executed four times per day (every 6 hours)

        Syncs RTC with NTP server

        Raises:
            RtcSyncError: If RTC sync fails
        """
        if not self.wifi.sync_rtc():
            raise RtcSyncError()

    def run(self):
        """Main scheduler loop

        Calculates time until next task and sleeps efficiently.
        This method does not return.
        """
        while True:
            # health.check() runs every iteration — it's the mechanism that detects
            # WiFi drop or HA going offline and exits run() via exception so the
            # outer loop can reconnect
            self.health.check()

            current_time = self.clock.now_utc()

            if current_time - self.last_six_hour_task >= SIX_HOUR_INTERVAL:
                self.six_hour_task()
                self.last_six_hour_task = current_time

            if current_time - self.last_minute_task >= MINUTE_INTERVAL:
                self.minute_task()
                self.last_minute_task = current_time

            current_time = self.clock.now_utc()
            time_until_next = MINUTE_INTERVAL - (current_time - self.last_minute_task)
            if time_until_next <= 0:
                time_until_next = MINUTE_INTERVAL
            time.sleep(time_until_next)
