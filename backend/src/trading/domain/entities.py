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
    side: Side

    entry_execution_ids: list[str] = None

    exit_execution_id: str = None
    
    # Costes reales (Requirement: PnL Realista)
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
        return f"{self.symbol} {self.side.value} {self.quantity.value} @ {self.entry_price.value} -> {self.exit_price.value} ({self.pnl_percentage:+.2f}%)"

    
@dataclass
class Position:
    """An open position not yet closed"""
    symbol: Symbol
    side: Side
    entry_price: Price
    entry_time: Timestamp
    quantity: Quantity

    def __post_init__(self) -> None:
        if self.quantity.value <= 0:
            raise ValueError("Quantity must be greater than 0")

    status: TradeStatus = TradeStatus.PENDING 
    
    
    target_quantity: Quantity = None 


    def add_partial_fill(self, fill_qty: Quantity, fill_price: Price) -> None:
        
        if self.target_quantity and self.quantity >= self.target_quantity:
            self.status = TradeStatus.EXECUTED
        else:
            self.status = TradeStatus.PARTIALLY_EXECUTED

    @property
    def is_filled_completely(self) -> bool:
        """Helper semántico para tu código"""
        return self.status == TradeStatus.EXECUTED

    def close(self, exit_price: Price, exit_time: Timestamp) -> Trade:

       return Trade(
        symbol=self.symbol,
        side=self.side,
        entry_price=self.entry_price,
        exit_price=exit_price,
        entry_time=self.entry_time,
        exit_time=exit_time,
        quantity=self.quantity,
     )

@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Result of a backtest."""
    symbol: Symbol
    interval: Interval
    strategy_name: str
    initial_capital: float
    final_capital: float
    trades: tuple[Trade, ...]
    
    @property
    def total_pnl(self) -> PnL:
        """Total profit and loss (can be negative)."""
        return PnL(Decimal(str(self.final_capital - self.initial_capital)))
    
    @property
    def total_pnl_percentage(self) -> float:
        """Total PnL as a percentage of initial capital."""
        if self.initial_capital == 0:
            return 0.0
        return float((self.total_pnl.value / Decimal(str(self.initial_capital))) * 100)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def total_winners(self) -> int:
        return sum(1 for trade in self.trades if trade.winner)

    @property
    def total_losers(self) -> int:
        return self.total_trades - self.total_winners

    def __str__(self) -> str:
        return f"{self.symbol} {self.interval.value} {self.strategy_name} {self.initial_capital} -> {self.final_capital} ({self.total_pnl_percentage:+.2f}%)"

    



@dataclass(slots=True)
class Candle:
    """Vela (candlestick) con timestamp."""

    @classmethod
    def from_static(cls, static: Candle_static) -> "Candle":
        """
        Convert a static candle to a dynamic candle
        """
        now = Timestamp(datetime.now())
        event_time = static.timestamp

        return cls(
            symbol=static.symbol,
            interval=static.interval,
            open_time=static.timestamp,
            close_time=static.timestamp, 
            ohlcv=static,
            ingestion_time=now,
            event_time=event_time,
            trades_count=0, 
            is_closed=True
        )
    
    symbol: Symbol
    interval: Interval
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


@dataclass(slots=True)
class Portfolio:
    """A portfolio entity"""
    name: str
    initial_capital: float
    current_capital: float
    total_return: float
    total_return_percentage: float
