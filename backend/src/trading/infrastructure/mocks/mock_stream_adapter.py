from ...domain.ports import StreamPort
from ...domain.value_objects import Symbol, Interval, Timestamp, Price, Quantity, Candle_static
from ...domain.entities import Candle
from typing import AsyncIterator
from decimal import Decimal
import asyncio
from datetime import datetime
import random

class MockStreamAdapter(StreamPort):
    """Mock stream adapter"""
    def __init__(self, base_price: float = 100.0, delay: float = 1.0) -> None:
        self._base_price = base_price
        self._delay = delay
        self._running = False
    
    async def get_live_candle(self, symbol: Symbol) -> Candle:
        pass


    async def stream_candle(self, symbol: Symbol, interval: Interval) -> AsyncIterator[Candle]:
        """Stream a candle from the mock stream"""
        self._running = True
        
        while self._running:
            price = self._base_price + random.uniform(-5, 5)
            
            candle = Candle.from_static(Candle_static(
                symbol=symbol,
                interval=interval,
                open=Price(Decimal(str(price))),
                high=Price(Decimal(str(price + 1))),
                low=Price(Decimal(str(price - 1))),
                close=Price(Decimal(str(price + 0.5))),
                volume=Quantity(Decimal("100")),
                timestamp=Timestamp(datetime.now())
            ))
            candle.is_closed = True  # Simular vela cerrada
            
            yield candle
            await asyncio.sleep(self._delay)
    
    async def connect(self) -> None:
        pass
    
    async def disconnect(self) -> None:
        self._running = False

if __name__ == "__main__":
    async def main():
        adapter = MockStreamAdapter()
        async for candle in adapter.stream_candle(Symbol("BTCUSDT"), Interval.M1):
            print(candle)

    asyncio.run(main())