from abc import ABC, abstractmethod
from trading.domain.entities import Candle
from trading.domain.value_objects import Symbol, Interval, Signal
from typing import List
#from asyncio import AsyncIterator

class Strategy(ABC):
    """Base class for all strategies"""
    
    def __init__(self, name: str, min_candles: int) -> None:
        self._name = name
        self._min_candles = min_candles
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def min_candles_required(self) -> int:
        return self._min_candles
        
    @abstractmethod
    def generate_signal(self, candles: List[Candle]) -> Signal:
        pass
    

class CandlestickPattern(ABC):
    """Base class for candlestick patterns"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def is_bullish(self) -> bool:
        """True if bullish pattern, False if bearish"""
        pass
    
    @property
    @abstractmethod
    def candles_required(self) -> int:
        """Number of candles needed to detect pattern"""
        pass
    
    @abstractmethod
    def is_pattern(self, candles: List[Candle]) -> bool:
        """Check if pattern is present in the last N candles"""
        pass


