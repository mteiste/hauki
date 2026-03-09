"""
System health monitoring for HAUKI
"""
from exceptions import NoHomeAssistantError, NoPricesError, NoWifiError


class HealthChecker:
    """Simple health status checker

    Checks components in order and raises on first failure.
    """

    def __init__(self, wifi, homeassistant, nordpool):
        """Initialize health checker

        Args:
            wifi: WiFi object
            homeassistant: HomeAssistant object
            nordpool: NordPool object
        """
        self.wifi = wifi
        self.ha = homeassistant
        self.nordpool = nordpool

    def check(self):
        """Check full system health.

        Checks in order:
        1. WiFi connection
        2. Home Assistant availability
        3. Current price data

        Raises:
            NoWifiError, NoHomeAssistantError, or NoPricesError
        """
        if not self.wifi.is_connected:
            raise NoWifiError()

        if not self.ha.is_online:
            raise NoHomeAssistantError()

        if not self.nordpool.available:
            raise NoPricesError(self.nordpool.unavailability_reason)
