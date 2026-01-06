from abc import ABC, abstractmethod, ABCMeta
from typing import AsyncIterator
from .value_objects import Symbol, Price, Interval, Candle_static, Timestamp
from .entities import Candle

"""The ports are the interfaces that the application uses to interact with the external world. Here we
define the interfaces for the exchange, the database and the trading engine."""

class ExchangePort(ABC):
    """Port for the exchange"""
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the exchange"""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange"""
    
    @abstractmethod
    async def get_historical_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        """Get candles from the exchange"""
        
    @abstractmethod
    async def get_candles_since(self, symbol: Symbol, interval: Interval, start_time: Timestamp) -> list[Candle_static]:
        """Get candles from start_time until now"""

class StreamPort(ABC):
    """Port for the exchange using a socket"""
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the exchange"""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange"""
    
    @abstractmethod
    async def get_live_candle(self, symbol: Symbol ) -> Candle:
        """"""

    @abstractmethod
    async def stream_candle(self, symbol: Symbol, interval: Interval) -> AsyncIterator[Candle]:
        """Stream a candle from the exchange"""

class StoragePort(ABC):
    """Port for the Postgres database"""
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the database"""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the database"""
    
    @abstractmethod
    async def save_candles(self, candles: list[Candle_static]) -> None:
        """Save candles to the database"""
    
    @abstractmethod
    async def get_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        """Get candles from the database"""

    @abstractmethod
    async def get_last_candle(self, symbol: Symbol, interval: Interval) -> Candle_static:
        """Get the last candle from the database"""
    
    @abstractmethod
    async def delete_candles(self, symbol: Symbol, interval: Interval, limit: int) -> int:
        """Delete candles from the database"""

    @abstractmethod
    async def count_candles(self, symbol: Symbol, interval: Interval) -> int:
        """Count the number of candles in the database"""
    







    