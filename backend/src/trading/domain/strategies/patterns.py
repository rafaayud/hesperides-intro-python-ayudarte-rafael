from trading.domain.strategies.base import CandlestickPattern
from trading.domain.value_objects import Signal
from typing import List
from trading.domain.entities import Candle


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

    def is_pattern(self, candles: List[Candle]) -> bool:
        pass




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

    def is_pattern(self, candles: List[Candle]) -> bool:
        pass


class BullishEngulfing(CandlestickPattern):
    """Bullish Engulfing pattern: A small body with a long upper shadow. Bullish pattern."""
    
    @property
    def name(self) -> str:
        return "Hammer"
    
    @property
    def is_bullish(self) -> bool:
        return True
    
    @property
    def candles_required(self) -> int:
        return 1

    def is_pattern(self, candles: List[Candle]) -> bool:
        pass


class BearishEngulfing(CandlestickPattern):
    """Bearish Engulfing pattern: A small body with a long lower shadow. Bearish pattern."""
    @property
    def name(self) -> str:
        return "Hammer"
    
    @property
    def is_bullish(self) -> bool:
        return True
    
    @property
    def candles_required(self) -> int:
        return 1

    def is_pattern(self, candles: List[Candle]) -> bool:
        pass

patterns_list = [
    Hammer(),
    ShootingStar(),
    BullishEngulfing(),
    BearishEngulfing(),
]