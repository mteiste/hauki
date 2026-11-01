"""
Electricity price data for HAUKI
Retrieves electricity price data from the Home Assistant ENTSO-E integration
"""
import time
from datetime import datetime

from exceptions import ConfigError

CHEAPEST_WINDOW_HOURS = {'cheapest_1h': 1, 'cheapest_2h': 2, 'cheapest_4h': 4}


class Prices:
    """Electricity price client.

    Retrieves electricity price data from Home Assistant via the ENTSO-E
    integration sensor (entsoe_prices).
    """

    def __init__(self, homeassistant, config):
        """Initialize price client.

        Args:
            homeassistant: Initialized HomeAssistant object
            config: Config object with price settings
        """
        self.ha = homeassistant
        settings = config.price_settings()
        self.entity_id = settings['entity_id']
        self.slot_duration = settings.get('slot_duration', 900)
        self.refresh_interval = settings.get('refresh_interval', 14400)
        # How the meter reports consumption to the electricity provider: 900 for
        # quarter-hour metering, 3600 for hourly. With hourly metering each whole hour
        # is billed at its average price, so windows have to start on the hour.
        self.metering_interval = settings.get('metering_interval', 900)
        self.prices = [None]  # Slot 0 is always None
        self.prices_start_utc = None
        self.last_update_timestamp = None
        self.unit = None
        self.tomorrow_valid = False
        self._refresh_error = None

    def _get_slot(self, timestamp):
        """Get slot index for given timestamp.

        Args:
            timestamp: UTC timestamp

        Returns:
            int: Slot index (0 if no data or out of range, 1+ for valid prices)
        """
        if self.prices_start_utc is None:
            return 0

        time_diff = timestamp - self.prices_start_utc
        slot_index = int(time_diff / self.slot_duration)

        # Offset by 1 for the None sentinel at index 0
        slot_with_offset = slot_index + 1

        if slot_with_offset < 1 or slot_with_offset >= len(self.prices):
            return 0

        return slot_with_offset

    def _refresh(self):
        """Internal: Fetch and parse price data from Home Assistant.

        Returns:
            bool: True if refresh succeeded, False if failed
        """
        state = self.ha.get_entity_state(self.entity_id)
        if state is None:
            self._refresh_error = "HA entity error"
            return False

        attrs = state.get('attributes', {})
        self.unit = attrs.get('unit_of_measurement', 'c/kWh')
        self.tomorrow_valid = attrs.get('tomorrow_valid', False)

        # raw_tomorrow is used regardless of tomorrow_valid: ENTSO-E publishes
        # the first slots of the next local day with today's auction, and every
        # slot present is a final price
        points = attrs.get('raw_today', []) + attrs.get('raw_tomorrow', [])

        # Start with None sentinel
        self.prices = [None]
        self.prices_start_utc = None

        expected_start = None
        for point in points:
            start = datetime.fromisoformat(point['start']).timestamp()
            # Stop at the first gap so that slot index arithmetic stays valid
            if expected_start is not None and start != expected_start:
                break
            if self.prices_start_utc is None:
                self.prices_start_utc = start
            self.prices.append(point['price_ct_kwh'])
            expected_start = start + self.slot_duration

        self.last_update_timestamp = time.time()
        self._refresh_error = None

        return True

    def get_current_price(self):
        """Get electricity price for current time slot.

        Returns:
            float: Price in cents/kWh, or None if unavailable
        """
        current_utc = time.time()
        slot_index = self._get_slot(current_utc)
        return self.prices[slot_index]

    def get_metering_price(self):
        """Get the price billed for the current metering period.

        Equals the current slot price when metering and price intervals match. With
        hourly metering it is the average of the hour's slots, since all consumption
        in that hour is billed at that average.

        Returns:
            float: Price in cents/kWh, or None if the period is not fully covered
        """
        slot = self._get_slot(time.time())
        if slot == 0:
            return None
        while not self._starts_metering_period(slot):
            slot -= 1
            if slot == 0:
                return None
        slots_per_period = self.metering_interval // self.slot_duration
        period = self.prices[slot:slot + slots_per_period]
        if len(period) < slots_per_period:
            return None
        return sum(period) / slots_per_period  # type: ignore

    def refresh(self):
        """Refresh price data if needed.

        Returns:
            bool: True if data is valid (no refresh needed or refresh succeeded),
                  False if refresh was needed but failed
        """
        if self.last_update_timestamp is None:
            return self._refresh()

        current_utc = time.time()
        slot_index = self._get_slot(current_utc)
        # Slot 0 means no valid data (clock not synced or out of range) — skip
        # the interval check and always attempt a fresh fetch
        if slot_index == 0:
            return self._refresh()

        time_since_update = current_utc - self.last_update_timestamp
        if time_since_update >= self.refresh_interval:
            return self._refresh()

        return True

    @property
    def unavailability_reason(self):
        """Reason why price data is unavailable, or None if available."""
        if self._refresh_error:
            return self._refresh_error
        if self.prices_start_utc is None:
            return "No price data fetched"
        return "No price for current hour"

    @property
    def current_slot(self):
        """Current price slot index based on UTC time."""
        return self._get_slot(time.time())

    @property
    def available(self):
        """Check if price data is available for current time.

        Returns:
            bool: True if current price is available, False otherwise
        """
        # Refresh is lazy — no network call happens until this property is read,
        # so constructing Prices before the network is up is safe
        self.refresh()
        return self.get_current_price() is not None

    def _slot_start(self, slot_index):
        # Slot index 1 corresponds to prices_start_utc
        return self.prices_start_utc + (slot_index - 1) * self.slot_duration

    def _starts_metering_period(self, slot_index):
        # Metering periods follow the local clock (e.g. whole local hours)
        local = time.localtime(self._slot_start(slot_index))
        seconds_since_midnight = local.tm_hour * 3600 + local.tm_min * 60 + local.tm_sec
        return seconds_since_midnight % self.metering_interval == 0

    def _average(self, first_slot, num_slots):
        # None unless every slot of the range has a price
        slots = self.prices[first_slot:first_slot + num_slots]
        if first_slot == 0 or len(slots) < num_slots:
            return None
        return sum(slots) / num_slots  # type: ignore

    def get_next_hour_price(self):
        """Get the average price of the hour following the current metering period.

        The hour starts with the next metering period, so with hourly metering it is
        the next whole hour, billed at exactly this price.

        Returns:
            float: Price in cents/kWh, or None if the hour is not fully covered
        """
        slot = self._get_slot(time.time())
        if slot == 0:
            return None
        slot += 1
        while slot < len(self.prices) and not self._starts_metering_period(slot):
            slot += 1
        return self._average(slot, 3600 // self.slot_duration)

    def get_day_average(self, days_ahead=0):
        """Get the average price of a local calendar day.

        Tomorrow counts only once the sensor marks it valid: ENTSO-E publishes the first
        slots of the next local day with today's auction, long before the rest is known.

        Args:
            days_ahead: 0 for today, 1 for tomorrow

        Returns:
            float: Price in cents/kWh, or None if the day is not fully covered
        """
        if days_ahead and not self.tomorrow_valid:
            return None
        now = time.localtime(time.time())
        # mktime normalises the day overflow and picks DST, so a day of 23 or 25 hours
        # gets its real length
        start, end = (
            time.mktime((now.tm_year, now.tm_mon, now.tm_mday + days, 0, 0, 0, 0, 0, -1))
            for days in (days_ahead, days_ahead + 1)
        )
        return self._average(self._get_slot(start), int((end - start) / self.slot_duration))

    def find_cheapest_window(self, hours):
        """Find next cheapest continuous time window within 24 hours.

        Searches from the next time slot onwards, limited to windows starting
        within the next 24 hours from now. Windows only start where a metering
        period starts (every slot with quarter-hour metering, on the hour with
        hourly metering).

        Args:
            hours: Duration in hours (e.g., 1, 2, or 4)

        Returns:
            tuple: (time_string, average_price) where time_string is "HH:MM" format
                   and average_price is the average price per hour in cents/kWh,
                   or None if insufficient data available
        """
        # Convert hours to number of slots
        num_slots = int(hours * 3600 / self.slot_duration)

        # Get current slot and start from next slot
        current_utc = time.time()
        current_slot = self._get_slot(current_utc)

        if current_slot == 0:
            return None

        # Start from the next slot — the current slot is already running and
        # cannot be acted upon
        start_slot = current_slot + 1

        # Limit search to windows starting within next 24 hours
        slots_in_24h = int(24 * 3600 / self.slot_duration)
        max_search_slot = min(current_slot + slots_in_24h, len(self.prices) - num_slots + 1)

        # Need at least num_slots available within 24h window
        if start_slot >= max_search_slot:
            return None

        min_sum = None
        min_slot_index = None
        for i in range(start_slot, max_search_slot):
            if not self._starts_metering_period(i):
                continue
            window_sum = sum(self.prices[i:i + num_slots])  # type: ignore
            if min_sum is None or window_sum < min_sum:
                min_sum = window_sum
                min_slot_index = i

        if min_slot_index is None:
            return None

        slot_timestamp = self._slot_start(min_slot_index)

        # Local time zone and DST come from the OS (/etc/localtime)
        time_string = time.strftime('%H:%M', time.localtime(slot_timestamp))

        # Calculate average price per hour
        average_price = min_sum / num_slots

        return (time_string, average_price)

    def get_box(self, item):
        """Get what a display box shows.

        Args:
            item: 'next_hour', 'today', 'tomorrow', 'cheapest_1h', 'cheapest_2h'
                  or 'cheapest_4h'

        Returns:
            tuple: (label, time_string or None, price or None)
        """
        if item == 'next_hour':
            return ('Next hour', None, self.get_next_hour_price())
        if item == 'today':
            return ('Today', None, self.get_day_average())
        if item == 'tomorrow':
            return ('Tomorrow', None, self.get_day_average(days_ahead=1))
        if item in CHEAPEST_WINDOW_HOURS:
            hours = CHEAPEST_WINDOW_HOURS[item]
            return (f'{hours}h', *(self.find_cheapest_window(hours) or (None, None)))
        raise ConfigError("Unknown display box", str(item))
