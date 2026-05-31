"""
Timezone conversion utilities for HAUKI
Handles conversion from UTC to local time with DST support
"""
import time


class LocalTimezone:
    """Local timezone converter with DST support.

    Converts UTC time to local time based on configuration rules.
    Supports automatic DST transitions based on configurable rules.
    """

    def __init__(self, config):
        """Initialize timezone converter.

        Args:
            config: Config object with timezone settings
        """
        tz = config.timezone_settings()
        self.name = tz['name']
        self.std_offset = tz['std_offset']
        self.dst_offset = tz['dst_offset']
        self.dst_rules = tz.get('dst_rules')

        self.dst_start_utc = None
        self.dst_end_utc = None
        self.dst_year = None

        if self.dst_rules and 'start' in self.dst_rules and 'end' in self.dst_rules:
            self._update_dst_transitions(time.gmtime(time.time())[0])

    def _find_nth_weekday(self, year, month, week, weekday):
        """Find the date of nth occurrence of weekday in month.

        Args:
            year: Year
            month: Month (1-12)
            week: Week number (1-5 for nth, -1 for last)
            weekday: Weekday (0=Monday, 6=Sunday)

        Returns:
            int: Day of month
        """
        first_day = time.mktime((year, month, 1, 0, 0, 0, 0, 0, 0))
        first_weekday = time.gmtime(first_day)[6]

        days_until = (weekday - first_weekday) % 7
        first_occurrence = 1 + days_until

        if week == -1:
            candidate = first_occurrence + (4 * 7)
            candidate_ts = time.mktime((year, month, candidate, 0, 0, 0, 0, 0, 0))
            candidate_dt = time.gmtime(candidate_ts)

            if candidate_dt[1] != month:
                candidate_ts -= 7 * 86400
                candidate_dt = time.gmtime(candidate_ts)

            return candidate_dt[2]
        else:
            return first_occurrence + ((week - 1) * 7)

    def _update_dst_transitions(self, year):
        """Calculate DST transition UTC timestamps for given year.

        Args:
            year: Year to calculate transitions for
        """
        start_rule = self.dst_rules['start']
        end_rule = self.dst_rules['end']

        start_day = self._find_nth_weekday(
            year, start_rule['month'], start_rule['week'], start_rule['weekday']
        )
        end_day = self._find_nth_weekday(
            year, end_rule['month'], end_rule['week'], end_rule['weekday']
        )

        self.dst_start_utc = time.mktime((
            year, start_rule['month'], start_day, start_rule['hour'], 0, 0, 0, 0, 0
        ))
        self.dst_end_utc = time.mktime((
            year, end_rule['month'], end_day, end_rule['hour'], 0, 0, 0, 0, 0
        ))
        self.dst_year = year

    def _is_dst(self, utc_timestamp):
        """Check if UTC timestamp is in DST period.

        Args:
            utc_timestamp: UTC timestamp (seconds since epoch)

        Returns:
            bool: True if in DST, False otherwise
        """
        if not self.dst_rules:
            return False

        year = time.gmtime(utc_timestamp)[0]
        if year != self.dst_year:
            self._update_dst_transitions(year)

        # Northern hemisphere: DST starts in spring and ends in autumn, both in the
        # same calendar year — a simple range check works
        if self.dst_rules['start']['month'] < self.dst_rules['end']['month']:
            return self.dst_start_utc <= utc_timestamp < self.dst_end_utc

        # Southern hemisphere: DST spans the year boundary (e.g. Oct→Mar), so the
        # active period wraps around — in DST if after start OR before end
        return utc_timestamp >= self.dst_start_utc or utc_timestamp < self.dst_end_utc

    def now_utc(self):
        """Get current UTC timestamp.

        Returns:
            int: UTC timestamp (seconds since epoch)
        """
        return time.time()

    def parse_iso_timestamp(self, iso_string):
        """Parse ISO 8601 datetime string to UTC timestamp.

        Args:
            iso_string: ISO 8601 formatted datetime string with timezone
                       (e.g., "2026-03-11T00:00:00+02:00" or "2026-03-11T22:00:00Z")

        Returns:
            int: UTC timestamp (seconds since epoch)
        """
        date_part, time_part = iso_string.split('T')
        year, month, day = [int(x) for x in date_part.split('-')]

        if '+' in time_part:
            time_str, tz_str = time_part.split('+')
            tz_sign = 1
        elif time_part.count('-') > 0:
            last_dash = time_part.rfind('-')
            time_str = time_part[:last_dash]
            tz_str = time_part[last_dash + 1:]
            tz_sign = -1
        elif time_part.endswith('Z'):
            time_str = time_part[:-1]
            tz_str = '00:00'
            tz_sign = 1
        else:
            time_str = time_part
            tz_str = '00:00'
            tz_sign = 1

        hour, minute, second = [int(x) for x in time_str.split(':')]
        tz_hours, tz_mins = [int(x) for x in tz_str.split(':')]
        tz_offset_seconds = tz_sign * (tz_hours * 3600 + tz_mins * 60)

        # MicroPython's mktime ignores the trailing (weekday, yearday, DST) fields
        local_timestamp = time.mktime((year, month, day, hour, minute, second, 0, 0, 0))
        utc_timestamp = local_timestamp - tz_offset_seconds

        return utc_timestamp

    def format_local_time(self, utc_timestamp):
        """Convert UTC timestamp to local time string.

        Args:
            utc_timestamp: UTC timestamp (seconds since epoch)

        Returns:
            str: Local time in HH:MM format
        """
        is_dst = self._is_dst(utc_timestamp)
        offset = (self.dst_offset if is_dst else self.std_offset) * 3600

        local_dt = time.gmtime(utc_timestamp + offset)
        return f"{local_dt[3]:02d}:{local_dt[4]:02d}"

    def is_tomorrow(self, utc_timestamp):
        """Check if UTC timestamp is tomorrow in local time.

        Args:
            utc_timestamp: UTC timestamp (seconds since epoch)

        Returns:
            bool: True if timestamp is tomorrow in local time
        """
        # DST doesn't cross day boundary, so single offset check is sufficient
        now = time.time()
        is_dst = self._is_dst(now)
        offset = (self.dst_offset if is_dst else self.std_offset) * 3600

        target_local_dt = time.gmtime(utc_timestamp + offset)
        now_local_dt = time.gmtime(now + offset)

        return (target_local_dt[0], target_local_dt[7]) > (
            now_local_dt[0], now_local_dt[7]
        )
