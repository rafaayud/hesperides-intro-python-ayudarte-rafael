from trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter
from trading.domain.value_objects import Symbol, TimeFrame
from trading.domain.entities import Candle
import asyncio
from typing import AsyncIterator



async def test_stream_candle(symbol:Symbol, interval:TimeFrame) -> None:
    loop = asyncio.get_event_loop()
    start_time = loop.time()
    
    async with BinanceStreamAdapter() as stream:
        async for candle in stream.stream_candle(symbol, interval):
            if loop.time() - start_time >= 20:
                break
            
            print(candle)
            await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(test_stream_candle(Symbol("BTCUSDT"), TimeFrame.M1))

