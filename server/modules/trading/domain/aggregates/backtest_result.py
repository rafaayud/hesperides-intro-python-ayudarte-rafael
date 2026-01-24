"""
BacktestResult Aggregate - Immutable result of a backtest.

Invariants:
1. initial_capital must be > 0
2. final_capital cannot be negative
3. trades must be a tuple (immutable)
4. symbol and interval must be defined
5. strategy_name cannot be empty
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple

from ..value_objects import Symbol, Interval, PnL
from ..entities import Trade


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """
    Immutable aggregate representing the result of a backtest.
    
    It is frozen because backtest results should not be modified
    once calculated.
    """
    symbol: Symbol
    interval: Interval
    strategy_name: str
    initial_capital: float
    final_capital: float
    trades: Tuple[Trade, ...]
    
    def __post_init__(self) -> None:
        # Invariant 1: initial capital must be positive
        if self.initial_capital <= 0:
            raise ValueError(
                f"initial_capital must be > 0, got: {self.initial_capital}"
            )
        
        # Invariant 2: final capital cannot be negative
        if self.final_capital < 0:
            raise ValueError(
                f"final_capital cannot be negative, got: {self.final_capital}"
            )
        
        # Invariant 3: trades must be tuple
        if not isinstance(self.trades, tuple):
            # frozen=True prevents modification, but we validate for safety
            object.__setattr__(self, 'trades', tuple(self.trades))
        
        # Invariant 4: symbol must be defined
        if self.symbol is None:
            raise ValueError("symbol cannot be None")
        
        # Invariant 5: strategy_name cannot be empty
        if not self.strategy_name or not self.strategy_name.strip():
            raise ValueError("strategy_name cannot be empty")
    
    # ==================
    # Calculated Properties
    # ==================
    
    @property
    def total_pnl(self) -> PnL:
        """
        Total Profit/Loss of the backtest.
        Can be negative (loss) or positive (profit).
        """
        return PnL(Decimal(str(self.final_capital - self.initial_capital)))
    
    @property
    def total_pnl_percentage(self) -> float:
        """Total PnL as percentage of initial capital."""
        if self.initial_capital == 0:
            return 0.0
        return float((self.total_pnl.value / Decimal(str(self.initial_capital))) * 100)

    @property
    def total_trades(self) -> int:
        """Total number of executed trades."""
        return len(self.trades)

    @property
    def total_winners(self) -> int:
        """Number of winning trades."""
        return sum(1 for trade in self.trades if trade.winner)

    @property
    def total_losers(self) -> int:
        """Number of losing trades."""
        return self.total_trades - self.total_winners

    @property
    def win_rate(self) -> float:
        """Percentage of winning trades."""
        if self.total_trades == 0:
            return 0.0
        return (self.total_winners / self.total_trades) * 100

    @property
    def avg_pnl_per_trade(self) -> PnL:
        """Average PnL per trade."""
        if self.total_trades == 0:
            return PnL(Decimal("0"))
        avg = self.total_pnl.value / self.total_trades
        return PnL(avg)

    @property
    def is_profitable(self) -> bool:
        """True if the backtest was profitable."""
        return self.total_pnl.is_positive

    def __str__(self) -> str:
        status = "✅" if self.is_profitable else "❌"
        return (
            f"{status} {self.symbol} [{self.interval.value}] - {self.strategy_name}\n"
            f"   Capital: ${self.initial_capital:,.2f} -> ${self.final_capital:,.2f} "
            f"({self.total_pnl_percentage:+.2f}%)\n"
            f"   Trades: {self.total_trades} "
            f"(W:{self.total_winners} L:{self.total_losers} WR:{self.win_rate:.1f}%)"
        )
