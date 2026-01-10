from dataclasses import dataclass
from decimal import Decimal
from ..value_objects import Symbol, Interval, PnL, Signal
from ..entities import Trade, Candle, Position
from ..strategies.base import Strategy




@dataclass
class Trader:
    """A trader that recives the live candles and executes a strategy."""

    id: str
    strategy: Strategy
    symbol: Symbol
    interval: Interval
    _candles: list[Candle]
    _position: Position = None

    def add_candle_and_execute_strategy(self, candle: Candle) -> Signal:
        """"""
    
        self._candles.append(candle)

        if len(self._candles) >= self.strategy.min_candles_required:
            return self.strategy.generate_signal(self._candles)
        else:
            return Signal.HOLD

        


    
