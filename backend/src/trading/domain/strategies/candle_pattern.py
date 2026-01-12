from .base import Strategy, CandlestickPattern
from ..value_objects import Signal, Candle_static
from ..utils import timed
from typing import List
from .patterns import patterns_list


class CandlePatternStrategy(Strategy):
    """Strategy that detects candlestick patterns"""
    
    def __init__(self, patterns: List[CandlestickPattern] | None = None) -> None:
        """Initialize the CandlePatternStrategy with the default patterns"""
        if patterns is None:
            patterns = patterns_list
        
        self._patterns = patterns
        max_candles = max(p.candles_required for p in patterns)
        
        super().__init__(
            name="Candle Patterns",
            min_candles=max_candles
        )
    
    @timed
    def generate_signal(self, candles: List[Candle_static]) -> Signal:
        if len(candles) < self._min_candles:
            return Signal.HOLD
        
        for pattern in self._patterns:
            if pattern.is_pattern(candles):
                return Signal.BUY if pattern.is_bullish else Signal.SELL
        
        return Signal.HOLD