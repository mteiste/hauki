"""
Timezone conversion utilities for HAUKI - Raspberry Pi implementation
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


class LocalTimezone:
    def __init__(self, config):
        tz = config.timezone_settings()
        self._tz = ZoneInfo(tz['name'])

    def now_utc(self):
        """Return current time as a UTC integer timestamp."""
        return int(datetime.now(timezone.utc).timestamp())

    def parse_iso_timestamp(self, iso_string):
        """Parse ISO 8601 string (with offset or Z) to UTC integer timestamp."""
        return int(datetime.fromisoformat(iso_string).astimezone(timezone.utc).timestamp())

    def format_local_time(self, utc_timestamp):
        """Convert UTC integer timestamp to local HH:MM string."""
        dt = datetime.fromtimestamp(utc_timestamp, tz=self._tz)
        return f"{dt.hour:02d}:{dt.minute:02d}"

    def is_tomorrow(self, utc_timestamp):
        """Return True if the UTC timestamp falls on tomorrow in local time."""
        today = datetime.now(self._tz).date()
        target = datetime.fromtimestamp(utc_timestamp, tz=self._tz).date()
        return target > today
