"""
Home Assistant API client for HAUKI - Raspberry Pi implementation
"""
import traceback

import requests


class HomeAssistant:
    def __init__(self, config):
        ha = config.homeassistant_settings()
        self.url = ha['url'].rstrip('/')
        self.token = ha['token']
        self.timeout = ha.get('timeout', 10)
        self.headers = {'Authorization': 'Bearer ' + self.token}
        self.api_endpoint = self.url + '/api/'
        self.states_endpoint_base = self.url + '/api/states/'

    @property
    def is_online(self):
        try:
            response = requests.get(self.api_endpoint, headers=self.headers, timeout=self.timeout)
            return response.status_code == 200
        except Exception:
            traceback.print_exc()
            return False

    def get_entity_state(self, entity_id):
        endpoint = self.states_endpoint_base + entity_id
        try:
            response = requests.get(endpoint, headers=self.headers, timeout=self.timeout)
            if response.status_code != 200:
                print(f"Error: status {response.status_code}")
                return None
            return response.json()
        except Exception:
            traceback.print_exc()
            return None
