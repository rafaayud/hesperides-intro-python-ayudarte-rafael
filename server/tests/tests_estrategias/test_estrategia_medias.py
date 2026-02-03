"""
Test unitario para la estrategia de cruce de medias (MeanCross).
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from modules.trading.domain.strategies.mean_cross import MeanCross
from modules.trading.domain.value_objects import (
    Signal, Candle_static, Symbol, Price, Quantity, Interval, Timestamp
)


def create_candle(close_price: float, index: int = 0) -> Candle_static:
    """Helper para crear una vela con un precio de cierre específico."""
    return Candle_static(
        symbol=Symbol("BTCUSDT"),
        open=Price(Decimal(str(close_price * 0.99))),
        high=Price(Decimal(str(close_price * 1.01))),
        low=Price(Decimal(str(close_price * 0.98))),
        close=Price(Decimal(str(close_price))),
        volume=Quantity(Decimal("100")),
        interval=Interval.M1,
        timestamp=Timestamp(datetime(2026, 1, 1) + timedelta(minutes=index))
    )


def create_candles_with_prices(prices: list[float]) -> list[Candle_static]:
    """Helper para crear una lista de velas a partir de precios de cierre."""
    return [create_candle(price, i) for i, price in enumerate(prices)]


class TestMeanCrossStrategy:
    """Tests para la estrategia MeanCross."""
    
    def test_init_default_values(self):
        """Verifica que los valores por defecto se inicializan correctamente."""
        strategy = MeanCross()
        assert strategy._slow_period == 50
        assert strategy._fast_period == 10
        assert strategy._min_candles == 51  # slow_period + 1
    
    def test_init_custom_values(self):
        """Verifica que se pueden usar valores personalizados."""
        strategy = MeanCross(slow_period=20, fast_period=5)
        assert strategy._slow_period == 20
        assert strategy._fast_period == 5
        assert strategy._min_candles == 21
    
    def test_hold_when_not_enough_candles(self):
        """Devuelve HOLD si no hay suficientes velas."""
        strategy = MeanCross(slow_period=10, fast_period=3)
        
        # Solo 5 velas, necesita 11 (slow_period + 1)
        candles = create_candles_with_prices([100] * 5)
        
        signal = strategy.generate_signal(candles)
        assert signal == Signal.HOLD
    
    def test_hold_when_no_cross(self):
        """Devuelve HOLD cuando no hay cruce de medias."""
        strategy = MeanCross(slow_period=10, fast_period=3)
        
        # Precios estables, sin cruce
        prices = [100.0] * 15
        candles = create_candles_with_prices(prices)
        
        signal = strategy.generate_signal(candles)
        assert signal == Signal.HOLD
    
    def test_buy_signal_on_golden_cross(self):
        """
        Return BUY when the fast MA crosses the slow MA upwards.
        (Golden Cross)
        """
        strategy = MeanCross(slow_period=10, fast_period=3)
        
        # Create prices where the fast MA (3) crosses upwards the slow MA (10)
        # First prices down, then up to generate the cross
        prices = [
            100, 99, 98, 97, 96, 95, 94, 93, 92, 91,  # Bajando - fast MA < slow MA
            90, 95, 100  # Rising quickly - fast MA > slow MA (cross!)
        ]
        candles = create_candles_with_prices(prices)
        
        signal = strategy.generate_signal(candles)
        assert signal == Signal.BUY
    
    def test_sell_signal_on_death_cross(self):
        """
        Return SELL when the fast MA crosses the slow MA downwards.
        (Death Cross)
        """
        strategy = MeanCross(slow_period=10, fast_period=3)
        
        # Create prices where the fast MA (3) crosses downwards the slow MA (10)
        # First prices up, then down to generate the cross
        prices = [
            90, 91, 92, 93, 94, 95, 96, 97, 98, 99,  # Rising - fast MA > slow MA
            100, 95, 90  # Falling quickly - fast MA < slow MA (cross!)
        ]
        candles = create_candles_with_prices(prices)
        
        signal = strategy.generate_signal(candles)
        assert signal == Signal.SELL
    
    def test_hold_when_fast_above_slow_no_cross(self):
        """
        Return HOLD when fast MA is above but already was before (no cross).
        """
        strategy = MeanCross(slow_period=10, fast_period=3)
        
        # Continuous bullish trend without new cross
        prices = [
            100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
            110, 111, 112  # Fast MA was already above slow MA
        ]
        candles = create_candles_with_prices(prices)
        
        signal = strategy.generate_signal(candles)
        assert signal == Signal.HOLD
    
    def test_hold_when_fast_below_slow_no_cross(self):
        """
        Return HOLD when fast MA is below but already was before (no cross).
        """
        strategy = MeanCross(slow_period=10, fast_period=3)
        
        # Continuous bearish trend without new cross
        prices = [
            110, 109, 108, 107, 106, 105, 104, 103, 102, 101,
            100, 99, 98  # Fast MA was already below slow MA
        ]
        candles = create_candles_with_prices(prices)
        
        signal = strategy.generate_signal(candles)
        assert signal == Signal.HOLD
    
    def test_strategy_name_format(self):
        """Verify that the strategy name is formatted correctly."""
        strategy = MeanCross(slow_period=50, fast_period=10)
        assert strategy._name == "MA Cross (10/50)"
        
        strategy2 = MeanCross(slow_period=200, fast_period=50)
        assert strategy2._name == "MA Cross (50/200)"
    
    def test_moving_average_calculation_accuracy(self):
        """
        Verify that the moving average calculations are correct.
        """
        strategy = MeanCross(slow_period=5, fast_period=3)
        
        # Known prices to verify calculations
        # Fast MA (3 last): (103 + 104 + 105) / 3 = 104
        # Slow MA (5 last): (101 + 102 + 103 + 104 + 105) / 5 = 103
        # Prev Fast MA (3 before the last): (102 + 103 + 104) / 3 = 103
        # Prev Slow MA (5 before the last): (100 + 101 + 102 + 103 + 104) / 5 = 102
        # Fast (104) > Slow (103) AND Prev Fast (103) <= Prev Slow (102)? 
        # 103 <= 102 is FALSE, so no cross -> HOLD
        prices = [100, 101, 102, 103, 104, 105]
        candles = create_candles_with_prices(prices)
        
        signal = strategy.generate_signal(candles)
        # No cross because prev_fast (103) > prev_slow (102)
        assert signal == Signal.HOLD
    
    def test_exact_cross_point_buy(self):
        """
        verify signal BUY when the exact cross point is reached.
        """
        strategy = MeanCross(slow_period=5, fast_period=2)
        
        # Designed for exact cross:
        # Last 2 for fast: [96, 100] -> fast_ma = 98
        # Last 5 for slow: [94, 95, 96, 96, 100] -> slow_ma = 96.2
        # Prev fast (without last): [96, 96] -> prev_fast = 96
        # Prev slow (without last): [93, 94, 95, 96, 96] -> prev_slow = 94.8
        # fast (98) > slow (96.2) AND prev_fast (96) <= prev_slow (94.8)?
        # 96 <= 94.8 is FALSE
        
        # Adjust to force the cross:
        prices = [90, 90, 90, 90, 90, 95]  # Big jump at the end
        candles = create_candles_with_prices(prices)
        
        signal = strategy.generate_signal(candles)
        assert signal == Signal.BUY
    
    def test_exact_cross_point_sell(self):
        """
        Verify signal SELL when the exact cross point is reached.
        """
        strategy = MeanCross(slow_period=5, fast_period=2)
        
        # Prices to force the downward cross
        prices = [110, 110, 110, 110, 110, 105]  # Big drop at the end
        candles = create_candles_with_prices(prices)
        
        signal = strategy.generate_signal(candles)
        assert signal == Signal.SELL
    
    

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
