from .base import CandlestickPattern
from ..value_objects import Candle_static
from typing import List


class Hammer(CandlestickPattern):
    """Hammer pattern: A small body with a long lower shadow. Bullish pattern."""
    
    @property
    def name(self) -> str:
        return "Hammer"
    
    @property
    def is_bullish(self) -> bool:
        return True
    
    @property
    def candles_required(self) -> int:
        return 1

    def is_pattern(self, candles: List[Candle_static]) -> bool:
        if len(candles) < 1:
            return False
        c = candles[-1]
        body = abs(c.close.value - c.open.value)
        lower_shadow = min(c.open.value, c.close.value) - c.low.value
        upper_shadow = c.high.value - max(c.open.value, c.close.value)
        
        # Hammer: lower shadow >= 2x body, small upper shadow
        return lower_shadow >= 2 * body and upper_shadow <= body * 0.5


class ShootingStar(CandlestickPattern):
    """Shooting Star pattern: A small body with a long upper shadow. Bearish pattern."""
    
    @property
    def name(self) -> str:
        return "Shooting Star"
    
    @property
    def is_bullish(self) -> bool:
        return False
    
    @property
    def candles_required(self) -> int:
        return 1

    def is_pattern(self, candles: List[Candle_static]) -> bool:
        if len(candles) < 1:
            return False
        c = candles[-1]
        body = abs(c.close.value - c.open.value)
        upper_shadow = c.high.value - max(c.open.value, c.close.value)
        lower_shadow = min(c.open.value, c.close.value) - c.low.value
        
        # Shooting Star: upper shadow >= 2x body, small lower shadow
        return upper_shadow >= 2 * body and lower_shadow <= body * 0.5


class BullishEngulfing(CandlestickPattern):
    """Bullish Engulfing: Current candle body engulfs previous bearish candle."""
    
    @property
    def name(self) -> str:
        return "Bullish Engulfing"
    
    @property
    def is_bullish(self) -> bool:
        return True
    
    @property
    def candles_required(self) -> int:
        return 2

    def is_pattern(self, candles: List[Candle_static]) -> bool:
        if len(candles) < 2:
            return False
        prev, curr = candles[-2], candles[-1]
        
        # Previous: bearish (close < open), Current: bullish (close > open)
        prev_bearish = prev.close.value < prev.open.value
        curr_bullish = curr.close.value > curr.open.value
        
        # Current body engulfs previous body
        engulfs = (curr.open.value <= prev.close.value and 
                   curr.close.value >= prev.open.value)
        
        return prev_bearish and curr_bullish and engulfs


class BearishEngulfing(CandlestickPattern):
    """Bearish Engulfing: Current candle body engulfs previous bullish candle."""
    
    @property
    def name(self) -> str:
        return "Bearish Engulfing"
    
    @property
    def is_bullish(self) -> bool:
        return False
    
    @property
    def candles_required(self) -> int:
        return 2

    def is_pattern(self, candles: List[Candle_static]) -> bool:
        if len(candles) < 2:
            return False
        prev, curr = candles[-2], candles[-1]
        
        # Previous: bullish (close > open), Current: bearish (close < open)
        prev_bullish = prev.close.value > prev.open.value
        curr_bearish = curr.close.value < curr.open.value
        
        # Current body engulfs previous body
        engulfs = (curr.open.value >= prev.close.value and 
                   curr.close.value <= prev.open.value)
        
        return prev_bullish and curr_bearish and engulfs

patterns_list = [
    Hammer(),
    ShootingStar(),
    BullishEngulfing(),
    BearishEngulfing(),
]