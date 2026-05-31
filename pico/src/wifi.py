"""
WiFi connection management for HAUKI
Handles WiFi connectivity for Raspberry Pi Pico W
"""
import sys
import time

import machine
import network
import ntptime

from config import Config


class WiFi:
    """WiFi connection manager for Raspberry Pi Pico W.

    Manages WLAN interface and provides methods for connecting,
    disconnecting, and monitoring WiFi status.
    """

    def __init__(self, config):
        """Initialize WiFi manager with WLAN interface.

        Args:
            config: Config object with WiFi settings
        """
        self.wlan = network.WLAN(network.STA_IF)
        self.config = config

    def connect(self):
        """Connect to WiFi network using config settings.

        Returns:
            bool: True if connected, False if failed
        """
        wifi = self.config.wifi_settings()
        ssid = wifi['ssid']
        password = wifi['password']
        timeout = wifi.get('timeout', 10)

        self.wlan.active(True)

        if self.wlan.isconnected():
            return True

        self.wlan.connect(ssid, password)

        start_time = time.time()
        while not self.wlan.isconnected():
            elapsed = time.time() - start_time
            if elapsed > timeout:
                self.wlan.active(False)
                return False
            time.sleep(0.5)

        return True

    def disconnect(self):
        """Disconnect from WiFi and disable WLAN interface.

        Returns:
            bool: True if disconnected successfully, False otherwise
        """
        if not self.wlan.isconnected():
            return True

        try:
            self.wlan.disconnect()
            self.wlan.active(False)
        except Exception as e:
            sys.print_exception(e)  # type: ignore
            return False

        return True

    def sync_rtc(self, ntp_host=None, timeout=10):
        """Synchronize RTC with NTP server.

        Args:
            ntp_host: Optional NTP server hostname (default uses ntptime's default)
            timeout: Timeout in seconds for NTP sync (default: 10)

        Returns:
            bool: True if RTC was synchronized successfully, False otherwise
        """
        if ntp_host:
            ntptime.host = ntp_host

        ntptime.timeout = timeout

        try:
            ntptime.settime()
        except Exception as e:
            sys.print_exception(e)  # type: ignore
            return False

        return True

    @property
    def is_connected(self):
        """Check if WiFi is currently connected.

        Returns:
            bool: True if connected, False otherwise
        """
        return self.wlan.isconnected()

    @property
    def ip_address(self):
        """Get current IP address.

        Returns:
            str or None: IP address if connected, None otherwise
        """
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return None

    @property
    def ssid(self):
        """Get connected network SSID.

        Returns:
            str or None: SSID if connected, None otherwise
        """
        if self.wlan.isconnected():
            return self.wlan.config('ssid')
        return None

    @property
    def rssi(self):
        """Get signal strength in dBm.

        Returns:
            int or None: Signal strength if connected and available, None otherwise
        """
        if self.wlan.isconnected():
            try:  # noqa: SIM105 [microPython]
                return self.wlan.status('rssi')
            except Exception:
                pass  # RSSI not available on all platforms
        return None
