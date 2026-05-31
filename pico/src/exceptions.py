"""
Error conditions for HAUKI
"""


class HaukiError(RuntimeError):
    def __init__(self, message, detail=""):
        self.message = message
        self.detail = detail
        super().__init__(message)


class NoWifiError(HaukiError):
    def __init__(self):
        super().__init__("Could not connect WiFi")


class NoHomeAssistantError(HaukiError):
    def __init__(self):
        super().__init__("Could not reach HA")


class NoPricesError(HaukiError):
    def __init__(self, detail=""):
        super().__init__("Could not fetch prices", detail)


class RtcSyncError(HaukiError):
    def __init__(self):
        super().__init__("Could not sync clock")
