"""
Home Assistant API client for HAUKI
Provides interface for checking HA status and making API calls
"""
import sys

import mrequests as requests


class HomeAssistant:
    """Home Assistant API client for Raspberry Pi Pico W.

    Provides methods to interact with Home Assistant REST API,
    including health checks and basic API operations.
    """

    def __init__(self, config):
        """Initialize Home Assistant client.

        Args:
            config: Config object with Home Assistant settings
        """
        self.config = config
        ha = config.homeassistant_settings()
        self.url = ha['url']
        self.token = ha['token']
        self.timeout = ha.get('timeout', 10)

        # Ensure URL doesn't have trailing slash
        if self.url and self.url.endswith('/'):
            self.url = self.url[:-1]

        self.headers = {'Authorization': 'Bearer ' + self.token}

        # Cache commonly used endpoint URLs
        self.api_endpoint = self.url + '/api/'
        self.states_endpoint_base = self.url + '/api/states/'

    @property
    def is_online(self):
        """Check if Home Assistant is online and responding.

        Returns:
            bool: True if HA is responding, False otherwise
        """
        try:
            response = requests.get(self.api_endpoint, headers=self.headers, timeout=self.timeout)
            status_code = response.status_code
            response.close()
        except Exception as e:
            sys.print_exception(e)  # type: ignore
            return False

        if status_code != 200:
            print(f"Error: status {status_code}")
            return False

        return True

    def get_entity_state(self, entity_id):
        """Get the state of a Home Assistant entity.

        Args:
            entity_id: The entity ID (e.g., 'sensor.temperature')

        Returns:
            dict: Entity state data including state and attributes, or None if failed
        """
        endpoint = self.states_endpoint_base + entity_id

        try:
            response = requests.get(endpoint, headers=self.headers, timeout=self.timeout)
            try:
                data = response.json()
            except Exception as e:
                sys.print_exception(e)  # type: ignore
                data = None
            status_code = response.status_code
            response.close()
        except Exception as e:
            sys.print_exception(e)  # type: ignore
            return None

        if status_code != 200:
            print(f"Error: status {status_code}")
        return data
