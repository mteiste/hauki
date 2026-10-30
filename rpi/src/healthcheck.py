"""
System health monitoring for HAUKI - Raspberry Pi implementation
"""
from exceptions import NoHomeAssistantError, NoPricesError


class HealthChecker:
    def __init__(self, homeassistant, prices):
        self.ha = homeassistant
        self.prices = prices

    def check(self):
        """Check HA and price data health; raise on first failure."""
        if not self.ha.is_online:
            raise NoHomeAssistantError()
        if not self.prices.available:
            raise NoPricesError(self.prices.unavailability_reason)
