"""
Configuration loader for HAUKI - Raspberry Pi implementation
"""
import json
import os


class Config:
    def __init__(self, path=None):
        if path is None:
            path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        with open(path) as f:
            self._config = json.load(f)

    def timezone_settings(self):
        return self._config['timezone']

    def homeassistant_settings(self):
        return self._config['homeassistant']

    def price_settings(self):
        return self._config['prices']

    def display_settings(self):
        return self._config.get('display', {})
