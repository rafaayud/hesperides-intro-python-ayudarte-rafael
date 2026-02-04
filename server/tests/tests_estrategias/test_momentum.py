import pytest
from modules.trading.domain.strategies import Momentum
from modules.trading.domain.value_objects import Signal, Candle_static, Price, Symbol, Interval, Timestamp
from decimal import Decimal
from datetime import datetime

def make_candle(open: float, high: float, low: float, close: float, volume: float = 1000) -> Candle_static:
    """Helper to create candles easily"""
    return Candle_static(
        symbol=Symbol("BTCUSDT"),
        interval=Interval.M1,
        timestamp=Timestamp(datetime.now()),
        open=Price(Decimal(str(open))),
        high=Price(Decimal(str(high))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(close))),
        volume=Decimal(str(volume))
    )






def test_hold_when_insufficient_candles():
        """Should HOLD when not enough candles"""
        strategy = Momentum(reference_period=5, threshold=0.02)
        candles = [make_candle(100, 101, 99, 100) for _ in range(3)]
        
        assert strategy.generate_signal(candles) == Signal.HOLD

def test_buy_signal_on_upward_momentum():
    """Should BUY when price increases above threshold"""
    strategy = Momentum(reference_period=3, threshold=0.02)
    
    # Price goes from 100 to 105 (5% increase > 2% threshold)
    candles = [
        make_candle(100, 101, 99, 100),   # reference
        make_candle(101, 102, 100, 101),
        make_candle(102, 103, 101, 103),
        make_candle(103, 106, 102, 105),  # current: +5%
    ]
    
    assert strategy.generate_signal(candles) == Signal.BUY

def test_sell_signal_on_downward_momentum():
    """Should SELL when price decreases below threshold"""
    strategy = Momentum(reference_period=3, threshold=0.02)
    
    # Price goes from 100 to 95 (-5% decrease < -2% threshold)
    candles = [
        make_candle(100, 101, 99, 100),  # reference
        make_candle(99, 100, 98, 99),
        make_candle(98, 99, 96, 97),
        make_candle(96, 97, 94, 95),     # current: -5%
    ]
    
    assert strategy.generate_signal(candles) == Signal.SELL

def test_hold_when_within_threshold():
    """Should HOLD when price change is within threshold"""
    strategy = Momentum(reference_period=3, threshold=0.05)
    
    # Price goes from 100 to 101 (1% < 5% threshold)
    candles = [
        make_candle(100, 101, 99, 100),
        make_candle(100, 101, 99, 100),
        make_candle(100, 101, 99, 100),
        make_candle(100, 102, 99, 101),  # +1%
    ]
    
    assert strategy.generate_signal(candles) == Signal.HOLD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])