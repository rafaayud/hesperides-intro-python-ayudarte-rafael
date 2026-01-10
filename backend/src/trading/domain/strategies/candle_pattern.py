from .base import Strategy, CandlestickPattern
from ..value_objects import Signal
from typing import List
from ..entities import Candle
from .patterns import patterns_list



class CandlePatternStrategy(Strategy):
    """Strategy that detects candlestick patterns"""
    
    def __init__(self, patterns: list[CandlestickPattern] | None = None) -> None:
        """Initialize the CandlePatternStrategy with the default patterns"""
        if patterns is None:
            patterns = patterns_list
        
        self._patterns = patterns
        max_candles = max(p.candles_required for p in patterns)
        
        super().__init__(
            name="Candle Patterns",
            min_candles=max_candles
        )
    
    def generate_signal(self, candles: list[Candle]) -> Signal:
        if len(candles) < self._min_candles:
            return Signal.HOLD
        
        for pattern in self._patterns:
            if pattern.is_pattern(candles):
                return Signal.BUY if pattern.is_bullish else Signal.SELL
        
        return Signal.HOLD