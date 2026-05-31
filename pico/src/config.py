"""
Configuration loader for HAUKI
Loads settings from config.json file
"""
import json


class Config:
    """Configuration manager for HAUKI.

    Loads and provides access to settings from config.json file.
    """

    def __init__(self):
        """Initialize and load configuration from JSON file."""
        with open('config.json', 'r') as f:
            self._config = json.load(f)

    def wifi_settings(self):
        """Get WiFi configuration.

        Returns:
            dict: WiFi settings (ssid, password, timeout)
        """
        return self._config['wifi']

    def timezone_settings(self):
        """Get timezone configuration.

        Returns:
            dict: Timezone settings (name, std_offset, dst_offset, dst_rules)
        """
        return self._config['timezone']

    def homeassistant_settings(self):
        """Get Home Assistant configuration.

        Returns:
            dict: Home Assistant settings (url, token, timeout)
        """
        return self._config['homeassistant']

    def nordpool_settings(self):
        """Get Nord Pool configuration.

        Returns:
            dict: Nord Pool settings (entity_id, slot_duration,
                refresh_interval)
        """
        return self._config['nordpool']
