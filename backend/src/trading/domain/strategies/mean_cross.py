from trading.domain.strategies.base import Strategy
from trading.domain.value_objects import Signal, Price
from typing import List, Tuple
from trading.domain.entities import Candle


class MeanCross(Strategy):
    """Mean Cross Strategy: Buy if the fast moving average crosses the slow moving average from below, and sell if it crosses from above."""
    
    def __init__(self, slow_period: int=50, fast_period: int=10) -> None:
        super().__init__(name=f"MA Cross ({fast_period}/{slow_period})", min_candles=slow_period+1)

        self._slow_period = slow_period
        self._fast_period = fast_period

    def generate_signal(self, candles: List[Candle]) -> Signal:
        if len(candles) < self._min_candles:
            return Signal.HOLDjajaj
        
        prices = [c.close for c in candles]
        
        # Moving averages
        fast_ma = sum(prices[-self._fast:]) / self._fast
        slow_ma = sum(prices[-self._slow:]) / self._slow
        
        # Previous moving averages (without last candle)
        prev_fast = sum(prices[-self._fast-1:-1]) / self._fast
        prev_slow = sum(prices[-self._slow-1:-1]) / self._slow
        
        # Detect cross
        if fast_ma > slow_ma and prev_fast <= prev_slow:
            return Signal.BUY
        elif fast_ma < slow_ma and prev_fast >= prev_slow:
            return Signal.SELL
        
        return Signal.HOLD



