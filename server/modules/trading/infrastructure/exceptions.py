"""Custom exceptions for the Binance adapter"""



class RateLimitError(Exception):
    """Raised when Binance rate limits us"""
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after

class IPBannedError(Exception):
    """Raised when Binance bans our IP"""
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after