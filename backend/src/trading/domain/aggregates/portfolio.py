"""
Portfolio Aggregate Root - Manages capital, positions and trades.

Invariants:
1. initial_capital must be > 0
2. available_capital cannot be negative
3. Cannot open position if the trader already has one open
4. Cannot close position that doesn't exist
5. Cannot register traders with duplicate IDs
6. Number of traders must match registered traders
"""
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Optional

from ..value_objects import PnL
from ..entities import Trade, Position, OrderResponse
from .trader import Trader  
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Portfolio:
    """
    Aggregate Root that manages capital and positions for multiple traders.
    
    Each trader is assigned a fraction of the total capital.
    Positions are tracked by trader_id.
    """
    initial_capital: Decimal
    traders: List[Trader]
    
    # Internal state
    _trades: Dict[str, List[Trade]] = field(default_factory=dict)
    _positions: Dict[str, Position] = field(default_factory=dict)  # trader_id -> Position
       
    
    
    
    def __post_init__(self) -> None:
        # Invariant 1: initial capital must be positive
        if self.initial_capital <= 0:
            raise ValueError(f"initial_capital must be > 0, got: {self.initial_capital}")

        # Invariant 2: number of traders must be positive
        _num_traders = len(self.traders)
        if _num_traders <= 0:
            raise ValueError(f"number of traders must be > 0, got: {_num_traders}")
    
        self._capital_for_trader = self.initial_capital / _num_traders 

        self._current_capital = {trader.id: PnL(self._capital_for_trader) for trader in self.traders}
        
        logger.info(f"Portfolio created with capital: {self.initial_capital} and {_num_traders} traders")

    @property
    def num_traders(self) -> int:
        return self._num_traders

    # ==================
    # Position Management
    # ==================

    def has_position(self, trader_id: str) -> bool:
        """Check if a trader has an open position."""
        return trader_id in self._positions

    def get_position(self, trader_id: str) -> Optional[Position]:
        """Get the position of a trader (None if none)."""
        return self._positions.get(trader_id)

    def can_open_position(self, trader_id: str, cost: Decimal) -> bool:
        """
        Check if a trader can open a position.
        
        Invariants verified:
        - The trader doesn't have an open position
        - There is enough available capital
        """
        if self.has_position(trader_id):
            return False
        if cost > self._available_capital:
            return False
        return True

    def open_position(self, trader_id: str, position: Position) -> None:
        """
        Open a position for a specific trader.
        
        Raises:
            ValueError: If trader already has position or insufficient capital
        """
        # Invariant 3: cannot open if already has position
        if self.has_position(trader_id):
            raise ValueError(f"Trader {trader_id} already has an open position")
        

        
        self._positions[trader_id] = position
        self._current_capital[trader_id] = Decimal("0")
        logger.info(
            f"Position opened for {trader_id}: {position.symbol} "
            f"{position.side.value} @ {position.entry_price}"
        )

    def close_position(self, trader_id: str, response: OrderResponse) -> None:
        """
        Close the position of a trader and record the trade.
        
        Args:
            trader_id: ID of the trader
            trade: The trade resulting from closing the position
            
        Raises:
            ValueError: If the trader doesn't have an open position
        """
        # Invariant 4: cannot close position that doesn't exist
        if not self.has_position(trader_id):
            raise ValueError(f"Trader {trader_id} has no position to close")
        trade = self.get_position(trader_id).close(response.price, response.timestamp)

        # Return capital + PnL
        
        self._current_capital[trader_id] += trade.pnl
        
        # Record trade
        trade_key = f"{trader_id}_{len(self._trades)}"
        self._trades[trade_key].append(trade)
        
        # Remove position
        self._positions[trader_id] = None
        
        logger.info(
            f"Position closed for {trader_id}: PnL={trade.pnl} ({trade.pnl_percentage:+.2f}%)"
        )

    # ==================
    # Query Methods
    # ==================

    @property
    def trades(self, trader_id: str) -> List[Trade]:
        """All completed trades (read-only)."""
        return self._trades[trader_id].copy()

    @property
    def positions(self, trader_id: str) -> Optional[Position]:
        """All open positions (read-only)."""
        return self._positions[trader_id]

    @property
    def total_pnl(self) -> PnL:
        """Total PnL of all closed trades."""
        if not self._trades:
            return PnL(Decimal("0"))

        total = Decimal("0")
        for trader_id in self.traders.id:
            for trade in self._trades[trader_id]:
                total += trade.pnl.value
        return PnL(total)

    def get_capital(self, trader_id: str) -> Decimal:
        """Get the capital of a trader."""
        return self._current_capital[trader_id].value

    @property
    def num_open_positions(self) -> int:
        """Number of open positions."""
        return sum(1 for position in self._positions.values() if position is not None)

    @property
    def num_completed_trades(self, trader_id: str) -> int:
        """Number of completed trades."""
        return len(self._trades[trader_id])

    def __repr__(self) -> str:
        return (
            f"<Portfolio capital={self.total_pnl.value:.2f}/{self.initial_capital:.2f} "
            f"positions={self.num_open_positions} trades={self.num_completed_trades} "
            f"PnL={self.total_pnl}>"
        )
