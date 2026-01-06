from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from .value_objects import Symbol, Price, Quantity, Timestamp, Side, Candle_static, TimeFrame, TradeStatus


@dataclass(frozen=True)
class Trade:
    """A trade entity"""
    symbol: Symbol
    price: Price
    quantity: Quantity
    timestamp: Timestamp
    side: Side
    status: TradeStatus


@dataclass(slots=True)
class Candle:
    """Vela (candlestick) con timestamp."""
    
    symbol: Symbol
    timeframe: TimeFrame
    open_time: Timestamp
    close_time: Timestamp
    ohlcv: Candle_static
    ingestion_time: Timestamp 
    event_time: Timestamp
    trades_count: int = 0
    is_closed: bool = True 

    @property
    def open(self) -> Price:
        return self.ohlcv.open
    
    @property
    def high(self) -> Price:
        return self.ohlcv.high
    
    @property
    def low(self) -> Price:
        return self.ohlcv.low
    
    @property
    def close(self) -> Price:
        return self.ohlcv.close
    
    @property
    def volume(self) -> Quantity:
        return self.ohlcv.volume

    def __str__(self) -> str:
        direction = "🟢" if self.close.value >= self.open.value else "🔴"
        change = self.close.value - self.open.value
        change_pct = (change / self.open.value) * 100
        status = "CLOSED" if self.is_closed else "OPEN"
        
        return (
            f"{direction} {self.symbol} [{self.timeframe.value}] ({status})\n"
            f"  Event time:   {self.event_time.timestamp:%Y-%m-%d %H:%M:%S:%f}\n"
            f"  Ingestion time:   {self.ingestion_time.timestamp:%Y-%m-%d %H:%M:%S:%f}\n"
            f"  Open time:   {self.open_time.timestamp:%Y-%m-%d %H:%M:%S:%f}\n"
            f"  Open:   ${self.open.value:>12,.2f}\n"
            f"  High:   ${self.high.value:>12,.2f}\n"
            f"  Low:    ${self.low.value:>12,.2f}\n"
            f"  Close:  ${self.close.value:>12,.2f}\n"
            f"  Change: ${change:>12,.2f} ({change_pct:+.2f}%)\n"
            f"  Volume: {self.volume.value:>12,.4f}\n"
            f"  Trades: {self.trades_count:>12,}"
        )
    
    def __repr__(self) -> str:
        status = "✓" if self.is_closed else "○"
        return f"<Candle {status} {self.symbol} {self.timeframe.value} @ {self.close.value}>"


@dataclass(slots=True)
class Portfolio:
    """A portfolio entity"""
    name: str
    initial_capital: float
    current_capital: float
    total_return: float
    total_return_percentage: float
