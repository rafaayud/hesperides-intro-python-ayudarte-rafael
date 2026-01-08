from dataclasses import dataclass
from decimal import Decimal
from trading.domain.value_objects import Symbol, Interval, PnL
from trading.domain.entities import Trade




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