from modules.trading.domain.ports import StreamPort
from modules.trading.domain.value_objects import Symbol, Interval
from modules.trading.domain.entities import Candle
from typing import AsyncIterator


class StreamingService:
    """Service for streaming data from a stream port"""

    def __init__(self, stream_port: StreamPort) -> None:
        self.stream_port = stream_port


    async def connect(self) -> None:
        """
        Connect to the stream port
        """
        await self.stream_port.connect()

    async def disconnect(self) -> None:
        """
        Disconnect from the stream port
        """
        await self.stream_port.disconnect()

    async def __aenter__(self) -> "StreamingService":
        """
        Enter the context manager
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Exit the context manager
        """
        await self.disconnect()

    async def stream_candle(self, symbol: Symbol, interval: Interval) -> AsyncIterator[Candle]:
        """
        Stream candles from the stream port
        Args:
            symbol: Symbol to stream
            interval: Interval to stream
        """
        async for candle in self.stream_port.stream_candle(symbol, interval):
            yield candle