from .base import Strategy
from ..value_objects import ExecutionMode, Signal, Candle_static
from typing import List
import random


class MockStrategy(Strategy):
    def __init__(self, name: str = "MockStrategy", min_candles: int = 1, mode: ExecutionMode = ExecutionMode.ON_CLOSE) -> None:
        super().__init__(name=name, min_candles=min_candles, mode=mode)

    
    @property
    def executes_on_tick(self) -> bool:
        """True if strategy should run on every tick."""
        return self._mode == ExecutionMode.ON_TICK
    
    @property
    def executes_on_close(self) -> bool:
        """True if strategy should run only on candle close."""
        return self._mode == ExecutionMode.ON_CLOSE
        
    
    def generate_signal(self, candles: List[Candle_static]) -> Signal:
        """
        Genera una señal de trading basada en las velas.
        
        Args:
            candles: Lista de Candle_static (solo OHLCV, inmutables)
            
        Returns:
            Signal.BUY, Signal.SELL, o Signal.HOLD
        """
        return random.choice([Signal.BUY, Signal.SELL, Signal.HOLD])