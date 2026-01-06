from trading.domain.entities import Candle
from trading.domain.value_objects import Symbol, Interval
from trading.domain.strategies.base import Strategy
from trading.domain.value_objects import Signal

class Momentum(Strategy):
    """Momentum Strategy: Buy if the price is going up, with a reference period a few candles ago. We take the
    percentage and compare it with a threshold."""

    def __init__(self, reference_period: int=14, threshold: float=0.02) -> None:
        super().__init__(name=f"Momentum ({reference_period})", min_candles=reference_period+1)
        self._reference_period = reference_period
        self._threshold = threshold

    def generate_signal(self, candles: list[Candle]) -> Signal:
        if len(candles) < self._min_candles:
            return Signal.HOLD

        prices = [c.close for c in candles]

        recent_price = prices[-1]
        reference_price = prices[-(self._reference_period+1)]

        percentage_change = (recent_price - reference_price) / reference_price

        if percentage_change > self._threshold:
            return Signal.BUY
        elif percentage_change < -self._threshold:
            return Signal.SELL
        else:
            return Signal.HOLD
