from .base import Strategy
from ..value_objects import Signal, Candle_static, ExecutionMode
from ..utils import timed
from typing import List


class MeanCross(Strategy):
    """Mean Cross Strategy: Buy if the fast moving average crosses the slow moving average from below, and sell if it crosses from above."""
    
    def __init__(self, slow_period: int=50, fast_period: int=10, mode: ExecutionMode = ExecutionMode.ON_CLOSE) -> None:
        super().__init__(name=f"MA Cross ({fast_period}/{slow_period})", min_candles=slow_period+1, mode=mode)
        self._slow_period = slow_period
        self._fast_period = fast_period

    @timed
    def generate_signal(self, candles: List[Candle_static]) -> Signal:
        if len(candles) < self._min_candles:
            return Signal.HOLD
        
        prices = [float(c.close.value) for c in candles]
        
        # Moving averages
        fast_ma = sum(prices[-self._fast_period:]) / self._fast_period
        slow_ma = sum(prices[-self._slow_period:]) / self._slow_period
        
        # Previous moving averages (without last candle)
        prev_fast = sum(prices[-self._fast_period-1:-1]) / self._fast_period
        prev_slow = sum(prices[-self._slow_period-1:-1]) / self._slow_period
        
        # Detect cross
        if fast_ma > slow_ma and prev_fast <= prev_slow:
            return Signal.BUY
        elif fast_ma < slow_ma and prev_fast >= prev_slow:
            return Signal.SELL
        
        return Signal.HOLD



