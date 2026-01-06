from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from datetime import datetime
import logging

#!!!!!!!!!!!!!!!!!!!!!!!!!!!Posible implementacion de metaclases


@dataclass(frozen=True, slots=True)
class Price():
    """A price value object"""
    #!!!!!!!!!!!!!!!!Posible implementacion de metaclases
    value: Decimal

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("Price must be greater than 0")

    def __str__(self) -> str:
        return f"{self.value}"
    
    def __float__(self) -> float:
        return float(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Price):
            return self.value == Decimal(str(other))

        if isinstance(other, Price):
            return self.value == other.value

    def __lt__(self, other: "Price") -> bool:
        return self.value < other.value
    
    def __le__(self, other: "Price") -> bool:
        return self.value <= other.value
    
    def __gt__(self, other: "Price") -> bool:
        return self.value > other.value
    
    def __ge__(self, other: "Price") -> bool:
        return self.value >= other.value
    
    def __add__(self, other: "Price") -> "Price":
        return Price(self.value + other.value)
    
    def __sub__(self, other: "Price") -> "Price":
        return Price(self.value - other.value)
    
    def __mul__(self, other: Decimal | int | float) -> "Price":
        return Price(self.value * Decimal(str(other)))
    
    def __truediv__(self, other: Decimal | int | float) -> "Price":
        return Price(self.value / Decimal(str(other)))
    
    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, slots=True)
class Symbol():
    """A trading Symbol of a pair of assets, like BTC/USDT."""
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!Posible implementacion de metaclases
    symbol: str

    def __post_init__(self) -> None:
        if not self.symbol.isalpha():
            raise ValueError("Base and quote must be alphabetic")

        if not self.symbol.endswith("USDT"):
            raise ValueError("Symbol must end with USDT")

    def __str__(self) -> str:
        return f"{self.symbol}"
    
    def __repr__(self) -> str:
        return f"Symbol({self.symbol})"

class TimeFrame(Enum):
    """Timeframes for candles."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MO1 = "1mo"
    MO3 = "3mo"
    Y1 = "1y"

    @property
    def max_candles(self) -> int:
        """Maximum number of candles for a given timeframe"""
        limits = {
            TimeFrame.M1: 10000,
            TimeFrame.M5: 10000,
            TimeFrame.M15: 10000,
            TimeFrame.H1: 10000,
            TimeFrame.H4: 10000,
            TimeFrame.D1: 10000,
            TimeFrame.W1: 1000,
            TimeFrame.MO1: 1000,
            TimeFrame.MO3: 400,
            TimeFrame.Y1: 200,
        }
        return limits.get(self, 1000)

@dataclass(frozen=True, slots=True)
class Quantity():
    """A quantity value object."""
    value: Decimal

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"Quantity cannot be negative: {self.value}")

    def __str__(self) -> str:
        return str(self.value)
    
    def __float__(self) -> float:
        return float(self.value)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Quantity):
            return self.value == other.value
        if isinstance(other, (int, float, Decimal)):
            return self.value == Decimal(str(other))
        return NotImplemented
    
    def __lt__(self, other: "Quantity") -> bool:
        return self.value < other.value
    
    def __le__(self, other: "Quantity") -> bool:
        return self.value <= other.value
    
    def __gt__(self, other: "Quantity") -> bool:
        return self.value > other.value
    
    def __add__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value + other.value)
    
    def __sub__(self, other: "Quantity") -> "Quantity":
        result = self.value - other.value
        if result < 0:
            raise ValueError("Resulting quantity would be negative")
        return Quantity(result)
    
    def __mul__(self, other: Decimal | int | float) -> "Quantity":
        return Quantity(self.value * Decimal(str(other)))

    @property
    def is_zero(self) -> bool:
        return self.value == Decimal("0")
            
@dataclass(frozen=True, slots=True)
class Timestamp():
    """A timestamp value object."""
    timestamp: datetime
    
@dataclass(frozen=True, slots=True)
class Candle_static:
    """OHLCV data of a candle."""
    symbol: Symbol
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity
    interval: TimeFrame
    timestamp: Timestamp

    def __str__(self) -> str:
        direction = "🟢" if self.close.value >= self.open.value else "🔴"
        change = self.close.value - self.open.value
        change_pct = (change / self.open.value) * 100
        
        return (
            f"{direction} {self.symbol} [{self.interval.value}]\n"
            f"  Time:   {self.timestamp.timestamp:%Y-%m-%d %H:%M:%S}\n"
            f"  Open:   ${self.open.value:>10,.2f}\n"
            f"  High:   ${self.high.value:>10,.2f}\n"
            f"  Low:    ${self.low.value:>10,.2f}\n"
            f"  Close:  ${self.close.value:>10,.2f}\n"
            f"  Change: ${change:>10,.2f} ({change_pct:+6.2f}%)\n"
            f"  Volume: {self.volume.value:>10,.4f}"
        )
    
    def __repr__(self) -> str:
        return f"<Candle {self.symbol} {self.interval.value} @ {self.close.value}>"
    
    @staticmethod
    def _print_table(candles: list['Candle_static'], logger: logging.Logger = None) -> None:
        """Print multiple candles as a table"""
        if not candles:
            return
        
        if logger is None:
            logger = logging.getLogger(__name__)
        
    
        
        header = f"\n{'Time':<20} {'Symbol':<10} {'Open':>12} {'High':>12} {'Low':>12} {'Close':>12} {'Change':>10}"
        separator = "=" * 100
        
        lines = [header, separator]
        
        for candle in candles:
            direction = "🟢" if candle.close.value >= candle.open.value else "🔴"
            change_pct = ((candle.close.value - candle.open.value) / candle.open.value) * 100
            
            lines.append(
                f"{candle.timestamp.timestamp:%Y-%m-%d %H:%M} "
                f"{str(candle.symbol):<10} "
                f"${candle.open.value:>11,.2f} "
                f"${candle.high.value:>11,.2f} "
                f"${candle.low.value:>11,.2f} "
                f"${candle.close.value:>11,.2f} "
                f"{direction}{abs(change_pct):>7.2f}%"
            )
        
        logger.debug("\n".join(lines)) 

class TradeStatus(Enum):
    """Status of a trade."""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"

class Signal(Enum):
    """Signal of a strategy."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class Side(Enum):
    """Side of a trade."""
    BUY = "BUY"
    SELL = "SELL"
    
    def opposite(self) -> "Side":
        return Side.SELL if self == Side.BUY else Side.BUY

__all__ = [
      "Symbol", "Price",
    "Quantity", "Timestamp", "Candle_static", "TimeFrame", "TradeStatus", "Signal", "Side"
]