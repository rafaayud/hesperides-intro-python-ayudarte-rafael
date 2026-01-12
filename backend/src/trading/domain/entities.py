from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from .value_objects import Symbol, Price, Quantity, Timestamp, Side, Candle_static, Interval, TradeStatus, PnL


@dataclass
class Trade:
    """A completed trade entity"""
    symbol: Symbol
    entry_price: Price
    exit_price: Price
    entry_time: Timestamp
    exit_time: Timestamp
    quantity: Quantity
    

    entry_execution_ids: list[str] = None

    exit_execution_id: str = None
    
    commission: Decimal = Decimal("0")

    @property
    def pnl(self) -> PnL:
        """Calculate profit and loss. Can be negative (loss) or positive (profit)."""
        # Calculate price difference per unit
        price_diff = self.exit_price.value - self.entry_price.value
        # Multiply by quantity to get total PnL
        total_pnl = price_diff * self.quantity.value
        return PnL(total_pnl)

    @property
    def pnl_percentage(self) -> float:
        """Calculate PnL as percentage of entry value"""
        entry_value = self.entry_price.value * self.quantity.value
        if entry_value == 0:
            return 0.0
        return float((self.pnl.value / entry_value) * 100)

    @property
    def winner(self) -> bool:
        """Returns True if trade was profitable"""
        return self.pnl.is_positive

    def __str__(self) -> str:
        return f"{self.symbol} {self.quantity.value} @ {self.entry_price.value} -> {self.exit_price.value} ({self.pnl_percentage:+.2f}%)"

    
@dataclass
class Position:
    """An open position not yet closed"""
    symbol: Symbol
    side: Side
    entry_price: Price
    entry_time: Timestamp
    quantity: Quantity
    status: TradeStatus = TradeStatus.PENDING 
    target_quantity: Quantity = None

    def __post_init__(self) -> None:
        if self.quantity.value <= 0:
            raise ValueError("Quantity must be greater than 0")
 

    def add_partial_fill(self, fill_qty: Quantity, fill_price: Price) -> None:
        
        if self.target_quantity and self.quantity >= self.target_quantity:
            self.status = TradeStatus.EXECUTED
        else:
            self.status = TradeStatus.PARTIALLY_EXECUTED

    @property
    def is_filled_completely(self) -> bool:
        """Returns True if the position is filled completely"""
        return self.status == TradeStatus.EXECUTED

    def close(self, exit_price: Price, exit_time: Timestamp) -> Trade:

       return Trade(
        symbol=self.symbol,
        entry_price=self.entry_price,
        exit_price=exit_price,
        entry_time=self.entry_time,
        exit_time=exit_time,
        quantity=self.quantity,
     )



@dataclass(slots=True)
class Candle:
    """
    Vela en tiempo real del WebSocket.
    
    Contiene:
    - ohlcv: Candle_static con los datos OHLCV (symbol, interval, OHLCV, timestamp)
    - Metadatos del WebSocket: close_time, event_time, ingestion_time, trades_count, is_closed
    
    Las propiedades symbol, interval, open_time, open, high, low, close, volume
    delegan a ohlcv para evitar duplicación.
    """
    
    # === Campos únicos de Candle (metadatos del WebSocket) ===
    ohlcv: Candle_static
    close_time: Timestamp
    event_time: Timestamp
    ingestion_time: Timestamp
    trades_count: int = 0
    is_closed: bool = True

    @classmethod
    def from_static(cls, static: Candle_static) -> "Candle":
        """Convierte un Candle_static (histórico) a Candle."""
        now = Timestamp(datetime.now())
        return cls(
            ohlcv=static,
            close_time=static.timestamp,
            event_time=static.timestamp,
            ingestion_time=now,
            trades_count=0,
            is_closed=True
        )

    
    @property
    def static_candle(self) -> Candle_static:
        return Candle_static(
            symbol=self.ohlcv.symbol,
            interval=self.ohlcv.interval,
            open=self.ohlcv.open,
            high=self.ohlcv.high,
            low=self.ohlcv.low,
            close=self.ohlcv.close,
            volume=self.ohlcv.volume,
            timestamp=self.ohlcv.timestamp,
        )


    # === Properties que delegan a ohlcv (sin duplicación) ===
    
    @property
    def symbol(self) -> Symbol:
        return self.ohlcv.symbol
    
    @property
    def interval(self) -> Interval:
        return self.ohlcv.interval
    
    @property
    def open_time(self) -> Timestamp:
        """open_time = ohlcv.timestamp (mismo concepto, diferente nombre)"""
        return self.ohlcv.timestamp

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
            f"{direction} {self.symbol} [{self.interval.value}] ({status})\n"
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
        return f"<Candle {status} {self.symbol} {self.interval.value} @ {self.close.value}>"


@dataclass(frozen=True, slots=True)
class Order:
    """
    Order entity.
    
    Before sending: order_id, execution_id are empty, status is PENDING.
    After response: all fields are filled by Binance.
    """
    trader_id: str
    symbol: Symbol
    side: Side
    quantity: Quantity
    price: Price
    order_id: str = ""
    execution_id: str = ""
    status: TradeStatus = TradeStatus.PENDING
    timestamp: Timestamp | None = None


@dataclass(frozen=True, slots=True)
class OrderResponse:
    """Response from exchange after order execution."""
    order_id: str
    symbol: Symbol
    quantity: Quantity
    price: Price  # Average fill price
    side: Side
    status: TradeStatus
    timestamp: Timestamp
        
    def __str__(self) -> str:
        return f"Order {self.order_id}: {self.side.value} {self.quantity} {self.symbol} @ {self.price} [{self.status.value}]"