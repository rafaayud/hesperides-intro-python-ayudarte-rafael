from dataclasses import dataclass
from decimal import Decimal
from trading.domain.value_objects import Symbol, Interval, PnL
from trading.domain.entities import Trade, Candle, Position
from trading.domain.aggregates.trader import Trader
from decimal import Decimal




@dataclass(slots=True)
class Portfolio:
    """A portfolio entity"""
    initial_capital: Decimal
    trades : dict[str, Trade]
    traders : dict[str, Trader]
    positions : dict[str, Position]

    @property
    def capital_for_each_trader(self) -> Decimal:
        return self.initial_capital / self.number_of_traders

    def add_trade(self, trade: Trade) -> None:
        """Add a trade to the portfolio."""
        self.trades[trade.id] = trade

    def add_position(self, position: Position, trader_id: str) -> None:
        """Add a position to the portfolio."""
        self.positions[trader_id] = position

    @property
    def PnL(self) -> PnL:
        """Calculate the total PnL of the portfolio."""
        return sum(trade.pnl for trade in self.trades.values())

    @property
    def unrealized_pnl(self) -> PnL:
        """Calculate the total unrealized PnL of the portfolio."""
        pass

        

    





