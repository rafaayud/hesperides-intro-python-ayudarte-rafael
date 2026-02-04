
import pytest
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from typing import List
from datetime import datetime

from modules.trading.domain.value_objects import  Candle_static, Price, Symbol, Interval, Timestamp
from modules.trading.domain.entities import Candle
from modules.trading.domain.strategies import CandlePatternStrategy, Hammer, ShootingStar, BullishEngulfing, BearishEngulfing
from modules.trading.domain.value_objects import Signal


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


def test_detects_hammer():
    """Should detect hammer pattern"""
    pattern = Hammer()

    candles = [make_candle(open=100, high=100.2, low=94, close=101)]
    
    assert pattern.is_pattern(candles) is True

def test_rejects_non_hammer():
    """Should reject candle without hammer characteristics"""
    pattern = Hammer()
    # Regular candle, no long lower shadow
    candles = [make_candle(open=100, high=102, low=99, close=101)]
    
    assert pattern.is_pattern(candles) is False



def test_detects_shooting_star():
    """Should detect shooting star pattern"""
    pattern = ShootingStar()
    # Shooting star: small body at bottom, long upper shadow (>=2x body), tiny lower shadow
    # body=1, upper_shadow=6, lower_shadow=0.2
    candles = [make_candle(open=100, high=107, low=99.8, close=101)]
    
    assert pattern.is_pattern(candles) is True

def test_rejects_non_shooting_star():
    """Should reject candle without shooting star characteristics"""
    pattern = ShootingStar()
    candles = [make_candle(open=100, high=101, low=99, close=100.5)]
    
    assert pattern.is_pattern(candles) is False





def test_detects_bullish_engulfing():
    """Should detect bullish engulfing pattern"""
    pattern = BullishEngulfing()
    candles = [
        make_candle(open=102, high=103, low=99, close=100),   # bearish
        make_candle(open=99, high=105, low=98, close=104),    # bullish engulfing
    ]
    
    assert pattern.is_pattern(candles) is True

def test_rejects_when_not_engulfing():
    """Should reject when current doesn't engulf previous"""
    pattern = BullishEngulfing()
    candles = [
        make_candle(open=102, high=103, low=99, close=100),
        make_candle(open=100, high=102, low=99, close=101),  # doesn't engulf
    ]
    
    assert pattern.is_pattern(candles) is False


def test_detects_bearish_engulfing():
    """Should detect bearish engulfing pattern"""
    pattern = BearishEngulfing()
    candles = [
        make_candle(open=100, high=103, low=99, close=102),   # bullish
        make_candle(open=103, high=104, low=98, close=99),    # bearish engulfing
    ]
    
    assert pattern.is_pattern(candles) is True


def test_hold_when_insufficient_candles():
    """Should HOLD when not enough candles"""
    strategy = CandlePatternStrategy()
    candles = [make_candle(100, 101, 99, 100)]
    
    # Strategy needs 2 candles (for engulfing patterns)
    assert strategy.generate_signal(candles) == Signal.HOLD

def test_buy_on_bullish_pattern():
    """Should BUY when bullish pattern detected"""
    strategy = CandlePatternStrategy(patterns=[Hammer()])
    # Hammer válido: body=1, lower_shadow=6, upper_shadow=0.2
    candles = [make_candle(open=100, high=100.2, low=94, close=101)]
    
    assert strategy.generate_signal(candles) == Signal.BUY

def test_sell_on_bearish_pattern():
    """Should SELL when bearish pattern detected"""
    strategy = CandlePatternStrategy(patterns=[ShootingStar()])
    # Shooting star válido: body=1, upper_shadow=6, lower_shadow=0.2
    candles = [make_candle(open=100, high=107, low=99.8, close=101)]
    
    assert strategy.generate_signal(candles) == Signal.SELL

def test_hold_when_no_pattern():
    """Should HOLD when no pattern detected"""
    strategy = CandlePatternStrategy()
    candles = [
        make_candle(100, 101, 99, 100.5),
        make_candle(100.5, 101.5, 99.5, 101),  # neutral candles
    ]
    
    assert strategy.generate_signal(candles) == Signal.HOLD


# ============== Run with: pytest test_velas.py -v ==============
if __name__ == "__main__":
    pytest.main([__file__, "-v"])