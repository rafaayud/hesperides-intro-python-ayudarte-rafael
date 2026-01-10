from ...domain.value_objects import Symbol, Interval, Timestamp, Candle_static, Price, Quantity
from ...domain.ports import storagePort



class MockStorageAdapter(storagePort):
    """Mock storage adapter"""

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def save_candles(self, candles: list[Candle_static]) -> None:
        pass

    async def get_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        pass

    async def get_last_candle(self, symbol: Symbol, interval: Interval) -> Candle_static:
        pass

    async def delete_candles(self, symbol: Symbol, interval: Interval, limit: int) -> int:
        pass

    async def count_candles(self, symbol: Symbol, interval: Interval) -> int:
        pass