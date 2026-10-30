"""
System health monitoring for HAUKI - Raspberry Pi implementation
"""
from exceptions import NoHomeAssistantError, NoPricesError


class HealthChecker:
    def __init__(self, homeassistant, prices):
        self.ha = homeassistant
        self.prices = prices

    def check(self):
        """Raise if there is no price for the current slot.

        HA only has to be reachable when prices need fetching. Day-ahead prices are
        final once published, so the prices already held stay valid through short
        network outages; a failed refresh is retried on the next check.
        """
        if self.prices.available:
            return
        if not self.ha.is_online:
            raise NoHomeAssistantError()
        raise NoPricesError(self.prices.unavailability_reason)
