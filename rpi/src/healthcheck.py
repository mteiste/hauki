"""
System health monitoring for HAUKI - Raspberry Pi implementation
"""
from exceptions import NoHomeAssistantError, NoPricesError


class HealthChecker:
    def __init__(self, homeassistant, nordpool):
        self.ha = homeassistant
        self.nordpool = nordpool

    def check(self):
        """Check HA and NordPool health; raise on first failure."""
        if not self.ha.is_online:
            raise NoHomeAssistantError()
        if not self.nordpool.available:
            raise NoPricesError(self.nordpool.unavailability_reason)
