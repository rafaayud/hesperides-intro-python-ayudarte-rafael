from abc import ABC, abstractmethod
from enum import Enum
from typing import List

from ..value_objects import Signal, Candle_static, ExecutionMode


class Strategy(ABC):
    """
    Base class for all strategies.
    
    Execution modes:
    - ON_CLOSE: Signal generated only when candle closes (safer, less noise)
    - ON_TICK: Signal generated on every price update (faster, more noise)
    
    Strategies work with Candle_static because they only need OHLCV.
    """
    
    def __init__(
        self, 
        name: str, 
        min_candles: int,
        mode: ExecutionMode = ExecutionMode.ON_CLOSE) -> None:

        self._name = name
        self._min_candles = min_candles
        self._mode = mode
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def min_candles_required(self) -> int:
        return self._min_candles
    
    @property
    def execution_mode(self) -> ExecutionMode:
        return self._mode
    
    @property
    def executes_on_tick(self) -> bool:
        """True if strategy should run on every tick."""
        return self._mode == ExecutionMode.ON_TICK
    
    @property
    def executes_on_close(self) -> bool:
        """True if strategy should run only on candle close."""
        return self._mode == ExecutionMode.ON_CLOSE
        
    @abstractmethod
    def generate_signal(self, candles: List[Candle_static]) -> Signal:
        """
        Genera una señal de trading basada en las velas.
        
        Args:
            candles: Lista de Candle_static (solo OHLCV, inmutables)
            
        Returns:
            Signal.BUY, Signal.SELL, o Signal.HOLD
        """
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
    def is_pattern(self, candles: List[Candle_static]) -> bool:
        """Check if pattern is present in the last N candles"""
        pass


