from ...domain.ports import ExchangePort
from ...domain.value_objects import Symbol, Interval, Timestamp, Candle_static, Price, Quantity
from ...domain.utils import AdapterMeta, timed_async
from decimal import Decimal
from datetime import datetime
import random
import asyncio
import logging


class MockExchangeAdapter(ExchangePort, metaclass=AdapterMeta):
    """
    Mock exchange adapter for testing.
    Generates simple random candle data.
    """
    
    def __init__(self, base_price: float = 100.0, seed: int | None = None):
        self._base_price = base_price
        self._current_price = base_price
        
        if seed is not None:
            random.seed(seed)
    
    async def connect(self) -> None:
        pass
    
    async def disconnect(self) -> None:
        pass
    
    def _generate_candle(self, symbol: Symbol, interval: Interval, timestamp: datetime) -> Candle_static:
        """Generate a simple OHLCV candle"""
        # Random price movement ±2%
        change = random.uniform(-0.02, 0.02)
        self._current_price *= (1 + change)
        
        close = self._current_price
        open_price = close * random.uniform(0.995, 1.005)
        high = max(open_price, close) * random.uniform(1.0, 1.01)
        low = min(open_price, close) * random.uniform(0.99, 1.0)
        volume = random.uniform(500, 1500)
        
        return Candle_static(
            symbol=symbol,
            interval=interval,
            timestamp=Timestamp(timestamp),
            open=Price(Decimal(str(round(open_price, 2)))),
            high=Price(Decimal(str(round(high, 2)))),
            low=Price(Decimal(str(round(low, 2)))),
            close=Price(Decimal(str(round(close, 2)))),
            volume=Quantity(Decimal(str(round(volume, 4)))),
        )
    
    def _interval_to_seconds(self, interval: Interval) -> int:
        mapping = {
            Interval.M1: 60,
            Interval.M5: 300,
            Interval.M15: 900,
            Interval.H1: 3600,
            Interval.H4: 14400,
            Interval.D1: 86400,
            Interval.W1: 604800,
            Interval.MO1: 2592000,
        }
        return mapping.get(interval, 60)
    
    @timed_async
    async def get_historical_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        """Generate historical candles"""
        candles = []
        seconds = self._interval_to_seconds(interval)
        now = datetime.now().timestamp()
        
        self._current_price = self._base_price
        
        for i in range(limit):
            ts = datetime.fromtimestamp(now - seconds * (limit - i - 1))
            candles.append(self._generate_candle(symbol, interval, ts))
        
        return candles
    
    async def get_candles_since(self, symbol: Symbol, interval: Interval, start_time: Timestamp) -> list[Candle_static]:
        """Get candles since start_time"""
        seconds = self._interval_to_seconds(interval)
        now = datetime.now().timestamp()
        diff = now - start_time.timestamp.timestamp()
        num_candles = int(diff / seconds) + 1
        
        return await self.get_historical_candles(symbol, interval, num_candles)

    @classmethod
    def deterministic(cls, base_price: float = 100.0, seed: int =101) -> "MockExchangeAdapter":
        return cls(base_price, seed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    async def main():
        logger = logging.getLogger(__name__)
        adapter = MockExchangeAdapter.deterministic()
        candles = await adapter.get_historical_candles(Symbol("BTCUSDT"), Interval.M1, 10)
        
        logger.info(Candle_static._print_table(candles))
    asyncio.run(main())