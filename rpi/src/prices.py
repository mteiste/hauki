"""
Electricity price data for HAUKI
Retrieves electricity price data from the Home Assistant ENTSO-E integration
"""
import time
from datetime import datetime


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
        self.prices = [None]  # Slot 0 is always None
        self.prices_start_utc = None
        self.last_update_timestamp = None
        self.unit = None
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

    def find_cheapest_window(self, hours):
        """Find next cheapest continuous time window within 24 hours.

        Searches from the next time slot onwards, limited to windows starting
        within the next 24 hours from now.

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

        # Find cheapest window using sliding window
        min_sum = sum(self.prices[start_slot:start_slot + num_slots])  # type: ignore
        min_slot_index = start_slot

        for i in range(start_slot + 1, max_search_slot):
            window_sum = sum(self.prices[i:i + num_slots])  # type: ignore

            if window_sum < min_sum:
                min_sum = window_sum
                min_slot_index = i

        # Calculate timestamp for the winning slot
        # Slot index 1 corresponds to prices_start_utc
        slot_timestamp = self.prices_start_utc + (min_slot_index - 1) * self.slot_duration

        # Local time zone and DST come from the OS (/etc/localtime)
        time_string = time.strftime('%H:%M', time.localtime(slot_timestamp))

        # Calculate average price per hour
        average_price = min_sum / num_slots

        return (time_string, average_price)
