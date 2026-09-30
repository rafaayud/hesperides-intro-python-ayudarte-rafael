from decimal import Decimal
from typing import Dict, Optional, List
import logging
import json

from modules.trading.domain.value_objects import Symbol, Side, Price, Quantity, Timestamp, TradeStatus, Interval
from modules.trading.domain.aggregates import Portfolio, Trader
from modules.trading.domain.entities import Position, Trade, OrderResponse
from modules.trading.domain.ports import PortfolioStoragePort
from modules.trading.application.services.strategy_factory import StrategyFactory

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Manages portfolio state: positions, trades, capital, persistence."""
    
    def __init__(
        self,
        storage: PortfolioStoragePort,
        portfolio: Portfolio | None = None) -> None:

        self._storage = storage
        self._portfolio = portfolio
    
    # ============ State Management ============
    
    def has_position(self, trader_id: str) -> bool:
        if self._portfolio is None:
            return False
        return self._portfolio.has_position(trader_id)
    
    def get_position(self, trader_id: str) -> Position | None:
        if self._portfolio is None:
            return None
        return self._portfolio.get_position(trader_id)
    
    def get_capital(self, trader_id: str) -> Decimal:
        if self._portfolio is None:
            raise ValueError("Portfolio not initialized")
        return self._portfolio.get_capital(trader_id)
    
    # ============ Position Operations ============
    
    async def open_position(self, trader_id: str, position: Position) -> None:
        """Open position and persist."""
        if self._portfolio is None:
            raise ValueError("Portfolio not initialized")
        self._portfolio.open_position(trader_id, position)
        await self._storage.save_position(
            self._portfolio.id,
            trader_id,
            position
        )

    async def close_position(self, trader_id: str, response: OrderResponse) -> Trade:
        """Close position, create trade, persist."""
        if self._portfolio is None:
            raise ValueError("Portfolio not initialized")
        trade = self._portfolio.close_position(trader_id, response)
        
        await self._storage.save_trade(
            self._portfolio.id,
            trader_id,
            trade
        )
        await self._storage.delete_positions(
            self._portfolio.id,
            trader_id
        )
        
        return trade
    
    # ============ Persistence ============

    async def load_portfolio(self, portfolio_id: str) -> Portfolio:
        """
        Load a portfolio from the database and reconstruct it completely.
        
        This method:
        1. Retrieves portfolio data (id, name, initial_capital)
        2. Retrieves all traders with their strategies
        3. Reconstructs traders using StrategyFactory and their saved parameters
        4. Creates the Portfolio aggregate
        5. Restores state (positions, trades, capital)
        
        Args:
            portfolio_id: ID of the portfolio to load
            
        Returns:
            Portfolio: Fully reconstructed portfolio
            
        Raises:
            ValueError: If portfolio not found
        """
        # Get portfolio data
        portfolio_data = await self._storage.get_portfolio_data(portfolio_id)
        if not portfolio_data:
            raise ValueError(f"Portfolio {portfolio_id} not found in database")
        
        # Reconstruct traders from database
        traders = []
        for trader_data in portfolio_data["traders"]:
            try:
                # Parse trader data
                trader_id = trader_data["trader_id"]
                strategy_name = trader_data["strategy_name"]
                symbol = Symbol(trader_data["symbol"])
                
                # Parse interval (can be enum name or value)
                interval_str = trader_data["interval"].upper()
                try:
                    interval = Interval[interval_str]
                except KeyError:
                    interval = Interval(trader_data["interval"])
            
                strategy_key = strategy_name.lower()
                
                params = trader_data.get("strategy_params") or {}
                if isinstance(params, str):
                    params = json.loads(params)
                strategy = StrategyFactory.create_strategy(
                    strategy_name=strategy_key,
                    strategy_params=params,
                )
                
                # Create trader
                trader = Trader(
                    id=trader_id,
                    strategy=strategy,
                    symbol=symbol,
                    interval=interval,
                    strategy_params=params,
                )
                traders.append(trader)
                
            except Exception as e:
                logger.error(f"Error reconstructing trader {trader_data.get('trader_id', 'unknown')}: {e}")
                raise ValueError(f"Failed to reconstruct trader: {e}")
        
        # Create portfolio
        portfolio = Portfolio(
            id=portfolio_data["id"],
            name=portfolio_data["name"],
            initial_capital=Decimal(str(portfolio_data["initial_capital"])),
            traders=traders
        )
        
        # Initialize and restore state
        self._portfolio = portfolio
        await self.restore_state()
        
        logger.info(f"Loaded portfolio {portfolio_id} with {len(portfolio.traders)} traders")
        return portfolio

    def initialize_portfolio(self, portfolio: Portfolio) -> None:
        """
        Initialize a new portfolio (will be saved on restore_state).
        
        Use this method when creating a new portfolio from scratch.
        The portfolio will be saved to the database when restore_state() is called.
        """
        self._portfolio = portfolio
    
    @property
    def portfolio(self) -> Portfolio:
        """Get the portfolio."""
        if self._portfolio is None:
            raise ValueError("Portfolio not initialized")
        return self._portfolio
    
    @property
    def traders(self) -> List[Trader]:
        """Get the traders from the portfolio."""
        if self._portfolio is None:
            return []
        return self._portfolio.traders
        
    
    async def restore_state(self) -> None:
        """
        Restore portfolio state from database (positions, trades, capital).
        
        If portfolio exists in database:
        - Restores open positions
        - Restores completed trades
        - Restores capital based on trades PnL
        
        If portfolio is new:
        - Saves portfolio to database
        """
        if self._portfolio is None:
            raise ValueError("Portfolio must be initialized before restoring state")
        
        # Check if portfolio exists in database
        portfolio_data = await self._storage.get_portfolio_data(self._portfolio.id)
        
        if portfolio_data:
            # Existing portfolio: restore state
            logger.info(f"Restoring existing portfolio state for {self._portfolio.id}")
            
            state = await self._storage.load_portfolio_state(self._portfolio.id)
            if state:
                # Build open positions dict (only for existing traders)
                trader_ids = {t.id for t in self._portfolio.traders}
                open_positions = {
                    pos_data["trader_id"]: Position(
                        symbol=Symbol(pos_data["symbol"]),
                        side=Side(pos_data["side"]),
                        entry_price=Price(pos_data["entry_price"]),
                        quantity=Quantity(pos_data["quantity"]),
                        entry_time=Timestamp(pos_data["entry_time"]),
                        status=TradeStatus.EXECUTED
                    ) for pos_data in state["open_positions"] if pos_data["trader_id"] in trader_ids}
                
                self._portfolio.restore_state(open_positions=open_positions, trades_by_trader=state.get("trades_by_trader", {}))
        else:
            # New portfolio: save it
            await self._storage.save_portfolio(self._portfolio)
            logger.info(f"Created new portfolio {self._portfolio.id}")
    
    async def save_portfolio(self) -> None:
        """Save portfolio to database."""
        if self._portfolio is None:
            raise ValueError("Portfolio must be initialized before saving")
        await self._storage.save_portfolio(self._portfolio)
    
    async def periodic_save(self) -> None:
        """Periodically save portfolio state (called by trading engine)."""
        if self._portfolio is None:
            return
        
        # Save portfolio
        await self._storage.save_portfolio(self._portfolio)
        
        # Save open positions
        for trader_id, position in self._portfolio.get_open_positions().items():
            await self._storage.save_position(self._portfolio.id, trader_id, position)
        
        # Save new trades and delete closed positions
        for trader_id, trades in self._portfolio.get_new_trades().items():
            for trade in trades:
                await self._storage.save_trade(self._portfolio.id, trader_id, trade)
            await self._storage.delete_positions(self._portfolio.id, trader_id)
            self._portfolio.clear_new_trades(trader_id)

        
    async def get_trades_by_trader(self, trader_id: str) -> List[Trade]:
        """Get the trades for a trader."""
        if self._portfolio is None:
            return []
        return self._portfolio.trades(trader_id)

    async def get_positions(self, portfolio_id: str) -> List[Position]:
        """Get all open positions for a portfolio from storage."""
        positions_data = await self._storage.get_open_positions(portfolio_id)
        positions = []
        for pos_data in positions_data:
            try:
                position = Position(
                    symbol=Symbol(pos_data["symbol"]),
                    side=Side(pos_data["side"]),
                    entry_price=Price(pos_data["entry_price"]),
                    quantity=Quantity(pos_data["quantity"]),
                    entry_time=Timestamp(pos_data["entry_time"]),
                    status=TradeStatus.EXECUTED
                )
                positions.append(position)
            except Exception as e:
                logger.warning(f"Could not parse position: {e}")
        return positions

    async def delete_portfolio(self, portfolio_id: str) -> None:
        """Delete a portfolio from the database."""
        await self._storage.delete_portfolio(portfolio_id)
    
    # ============ Context Manager ============
    
    async def connect(self) -> None:
        await self._storage.connect()
    
    async def disconnect(self) -> None:
        await self._storage.disconnect()
    
    # ============ Context Manager ============
    
    async def __aenter__(self) -> "PortfolioManager":
        """Enter the context manager"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the context manager"""
        await self.disconnect()
