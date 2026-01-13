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

        self._trades = {trader.id: [] for trader in self.traders}
        
        logger.info(f"Portfolio created with capital: {self.initial_capital} and {_num_traders} traders")

    @property
    def num_traders(self) -> int:
        return self._num_traders

    # ==================
    # Position Management
    # ==================

    

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
        self._current_capital[trader_id] = PnL(Decimal("0"))
        logger.info(
            f"Position opened for {trader_id}: {position.symbol} "
            f"{position.side.value} @ {position.entry_price}"
        )

    def close_position(self, trader_id: str, response: OrderResponse) -> None:
        """
        Close the position of a trader and record the trade.
        
        Args:
            trader_id: ID of the trader
            response: The response from the order execution
            
        Raises:
            ValueError: If the trader doesn't have an open position
        """
        # Invariant 4: cannot close position that doesn't exist
        if not self.has_position(trader_id):
            raise ValueError(f"Trader {trader_id} has no position to close")

        trade = self.get_position(trader_id).close(response.price, response.timestamp)
        self._positions[trader_id] = None


        # Return capital + PnL
        
        self._current_capital[trader_id] += PnL(trade.exit_price.value * trade.quantity.value)
        
        # Record trade
       
        self._trades[trader_id].append(trade)
        
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

    
    def has_position(self, trader_id: str) -> bool:
        """Check if a trader has an open position."""
        return self._positions.get(trader_id) is not None

    def get_position(self, trader_id: str) -> Optional[Position]:
        """Get the position of a trader (None if none)."""
        return self._positions.get(trader_id)

    def can_open_position(self, trader_id: str) -> bool:
        """
        Check if a trader can open a position.
        
        Invariants verified:
        - The trader doesn't have an open position
        - There is enough available capital
        """
        if self.has_position(trader_id):
            return False

        return True

    @property
    def total_pnl(self) -> PnL:
        """Total PnL of all closed trades."""
        if not self._trades:
            return PnL(Decimal("0"))

        total = Decimal("0")
        for trader in self.traders:
            trader_id = trader.id
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
        """Debugging representation."""
        return (
            f"<Portfolio initial={self.initial_capital:.2f} "
            f"positions={self.num_open_positions} "
            f"traders={len(self.traders)} "
            f"PnL={self.total_pnl.value:+.2f}>"
        )
    
    def __str__(self) -> str:
        """Human-readable representation with per-trader breakdown."""
        total_trades = sum(len(trades) for trades in self._trades.values())
        pnl_pct = (self.total_pnl.value / self.initial_capital) * 100 if self.initial_capital > 0 else 0
        
        lines = [
            f"Portfolio Summary",
            f"  Initial Capital: ${self.initial_capital:,.2f}",
            f"  Total PnL:       ${self.total_pnl.value:+,.2f} ({pnl_pct:+.2f}%)",
            f"  Open Positions:  {self.num_open_positions}",
            f"  Total Trades:    {total_trades}",
            f""
        ]
        
        for trader in self.traders:
            trader_trades = self._trades[trader.id]
            trader_pnl = sum(trade.pnl.value for trade in trader_trades)
            position_status = "OPEN" if self.has_position(trader.id) else "CLOSED"
            
            lines.append(
                f"[{trader.id}] {len(trader_trades)} trades | "
                f"PnL=${trader_pnl:+,.2f} | position={position_status}"
            )
            
            # Lista de trades del trader
            if trader_trades:
                for i, trade in enumerate(trader_trades, 1):
                    pnl_sign = "+" if trade.pnl.value >= 0 else ""
                    lines.append(
                        f"  {i}. {trade.symbol} | "
                        f"Entry=${trade.entry_price.value:.2f} Exit=${trade.exit_price.value:.2f} | "
                        f"PnL={pnl_sign}${trade.pnl.value:.2f} ({trade.pnl_percentage:+.2f}%)"
                    )
            else:
                lines.append(f"  (no trades yet)")
            
            lines.append("")  # Línea en blanco entre traders
        
        return "\n".join(lines)
