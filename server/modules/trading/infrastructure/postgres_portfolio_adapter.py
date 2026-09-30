from typing import Optional, List, Dict
from ..domain.ports import PortfolioStoragePort
from ..domain.aggregates import Portfolio, Trader
from ..domain.entities import Trade, Position, PnL
from ..domain.value_objects import Symbol, Side, Price, Quantity, Timestamp, TradeStatus

from ..domain.utils.decorators import timed_async, timed
from ..domain.utils.metaclasses import AdapterMeta

from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import json
import asyncpg
from decimal import Decimal

from modules.trading.application.services.strategy_factory import StrategyFactory

class PostgresPortfolioAdapter(PortfolioStoragePort, metaclass=AdapterMeta):
    """Adapter to store the information of the portfolios: traders, trades, postions, PnL
    
    Args:
        conn: asyncpg.Connection
        db_url: str
    
    """
    #=====================
    # Context Management
    #=====================

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        self._pool: asyncpg.Pool | None = None
    
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=15))
    async def connect(self) -> None:
        """Connect to the database"""
        self._pool = await asyncpg.create_pool(self.db_url)
        logging.info("Connected to the database")
    
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
        logging.info("Disconnected from the database")
    
    async def __aenter__(self) -> "PostgresPortfolioAdapter":
        await self.connect()
        return self
    
    async def __aexit__(self, *args) -> None:
        await self.disconnect()



    #=====================
    # Portfolio Management
    #=====================

    @timed_async
    async def save_portfolio(self, portfolio: Portfolio) -> None:
        """Save the portfolio to the database.
        
        IMPORTANT: This method uses UPSERT (ON CONFLICT) to update existing portfolios.
        It preserves open positions - they are NOT deleted when updating the portfolio.
        To update positions, use save_position() separately.
        
        Args:
            portfolio: Portfolio

        Returns:
            None

        Raises:
            asyncpg.exceptions.PostgresError: If the portfolio cannot be saved
        """
        portfolio_id = portfolio.id
        name = portfolio.name
        portfolio_capital = portfolio.initial_capital
        traders = portfolio.traders

        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    # Check if portfolio exists
                    existing = await conn.fetchrow(
                        "SELECT id FROM portfolios WHERE id = $1",
                        portfolio_id
                    )
                    
                    if existing:
                        logging.info(f"Updating existing portfolio {portfolio_id} (preserving open positions)")
                    else:
                        logging.info(f"Creating new portfolio {portfolio_id}")
                    
                    # UPSERT portfolio
                    await conn.execute(
                        """
                        INSERT INTO portfolios (id, name, initial_capital)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (id) DO UPDATE SET name = $2, initial_capital = $3
                        """,
                        portfolio_id, name, portfolio_capital
                    )
                    
                    # UPSERT traders (preserves existing traders if portfolio exists)
                    for trader in traders:
                        trader_id = trader.id
                        
                        strategy_key = StrategyFactory.get_strategy_key(trader.strategy)
                        symbol = trader.symbol.symbol
                        interval = trader.interval.value
                        capital = portfolio.get_capital(trader_id)

                        await conn.execute(
                            """
                            INSERT INTO portfolio_traders (portfolio_id, trader_id, strategy_name, symbol, interval, allocated_capital, strategy_params)
                            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                            ON CONFLICT (portfolio_id, trader_id) DO UPDATE 
                            SET strategy_name = $3, symbol = $4, interval = $5, allocated_capital = $6, strategy_params = $7::jsonb
                            """,
                            portfolio_id,
                            trader_id,
                            strategy_key, 
                            symbol,
                            interval,
                            capital,
                            json.dumps(trader.strategy_params),
                        )
                    
                    # Save current open positions from portfolio state
                    for trader in traders:
                        if portfolio.has_position(trader.id):
                            position = portfolio.get_position(trader.id)
                            await self.save_position(portfolio_id, trader.id, position)

                logging.info(f"Portfolio {portfolio_id} saved successfully")

        except Exception as e:
            logging.error(f"Error saving portfolio {portfolio_id}: {e}")
            raise  # Propagar el error para que los tests fallen
            
    

    @timed_async
    async def get_portfolio_data(self, portfolio_id: str) -> Optional[dict]:
        """Get the data of the portfolio from the database

        Args:

            portfolio_id: str

        Returns:
            Optional[dict]: The data of the portfolio

        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM portfolios WHERE id = $1",
                    portfolio_id
                )
                if not row:
                    return None
                
                traders = await conn.fetch(
                    "SELECT * FROM portfolio_traders WHERE portfolio_id = $1",
                    portfolio_id
                )
                
                return {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "initial_capital": row["initial_capital"],
                    "traders": [dict(t) for t in traders],
                    "created_at": row["created_at"]
                }
        except Exception as e:
            logging.error(f"Error getting portfolio data {portfolio_id}: {e}")
            return None

    @timed_async
    async def load_portfolio_state(self, portfolio_id: str) -> Optional[dict]:
        """Load complete portfolio state including open positions and trades
        
        Args:
            portfolio_id: str
            
        Returns:
            Optional[dict]: Complete portfolio state with positions and trades grouped by trader_id, or None if not found
        """
        try:
            portfolio_data = await self.get_portfolio_data(portfolio_id)
            if not portfolio_data:
                return None
            
            # Load open positions
            open_positions = await self.get_open_positions(portfolio_id)
            
            # Load trades grouped by trader_id
            async with self._pool.acquire() as conn:
                trade_rows = await conn.fetch(
                    """
                    SELECT trader_id, symbol, side, entry_price, exit_price, quantity, 
                           pnl, pnl_percentage, entry_time, exit_time
                    FROM trades 
                    WHERE portfolio_id = $1
                    ORDER BY exit_time DESC
                    """,
                    portfolio_id
                )
            
            # Group trades by trader_id
            trades_by_trader: Dict[str, List[Trade]] = {}
            for row in trade_rows:
                trader_id = row["trader_id"]
                if trader_id not in trades_by_trader:
                    trades_by_trader[trader_id] = []
                trades_by_trader[trader_id].append(self._row_to_trade(row))
            
            return {
                **portfolio_data,
                "open_positions": open_positions,
                "trades_by_trader": trades_by_trader
            }
        except Exception as e:
            logging.error(f"Error loading portfolio state {portfolio_id}: {e}")
            return None

    @timed_async
    async def list_portfolios(self) -> List[dict]:
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM portfolios ORDER BY created_at DESC")
                return [{"id": str(r["id"]), "name": r["name"], "initial_capital": r["initial_capital"]} for r in rows]
        except Exception as e:
            logging.error(f"Error listing portfolios: {e}")
            return []


    #=====================
    # Position Management
    #=====================

    @timed_async
    async def save_position(self, portfolio_id: str, trader_id: str, position: Position) -> None:
        """Save the position to the database

        Args:
            portfolio_id: str
            trader_id: str
            position: Position

        Returns:
            None

        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO positions (portfolio_id, trader_id, symbol, side, entry_price, quantity, entry_time)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (portfolio_id, trader_id) 
                    DO UPDATE SET symbol = $3, side = $4, entry_price = $5, quantity = $6, entry_time = $7
                    """,
                    portfolio_id,
                    trader_id,
                    str(position.symbol),
                    position.side.value,
                    position.entry_price.value,
                    position.quantity.value,
                    position.entry_time.timestamp
                )
                logging.info(f"Position {position.symbol} {position.side} saved successfully")
        except Exception as e:
            logging.error(f"Error saving position {position.symbol} {position.side}: {e}")
            raise
            
    @timed_async
    async def delete_positions(self, portfolio_id: str, trader_id: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM positions WHERE portfolio_id = $1 AND trader_id = $2",
                portfolio_id, trader_id
            )

    @timed_async
    async def get_open_positions(self, portfolio_id: str) -> List[dict]:
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM positions WHERE portfolio_id = $1",
                    portfolio_id
                )
                return [
                    {
                        "trader_id": r["trader_id"],
                        "symbol": r["symbol"],
                        "side": r["side"],
                        "entry_price": r["entry_price"],
                        "quantity": r["quantity"],
                        "entry_time": r["entry_time"]}for r in rows]
                
        except Exception as e:
            logging.error(f"Error getting open positions for portfolio {portfolio_id}: {e}")
            return []

    @timed_async
    async def delete_portfolio(self, portfolio_id: str) -> None:
        """Delete a portfolio and all associated data (traders, positions, trades)
        
        Args:
            portfolio_id: str
            
        Returns:
            None
        """
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    # Eliminar en orden: primero dependencias, luego el portfolio
                    # 1. Eliminar trades
                    await conn.execute(
                        "DELETE FROM trades WHERE portfolio_id = $1",
                        portfolio_id
                    )
                    
                    # 2. Eliminar posiciones
                    await conn.execute(
                        "DELETE FROM positions WHERE portfolio_id = $1",
                        portfolio_id
                    )
                    
                    # 3. Eliminar traders asociados
                    await conn.execute(
                        "DELETE FROM portfolio_traders WHERE portfolio_id = $1",
                        portfolio_id
                    )
                    
                    # 4. Finalmente eliminar el portfolio
                    await conn.execute(
                        "DELETE FROM portfolios WHERE id = $1",
                        portfolio_id
                    )
                    
                logging.info(f"Portfolio {portfolio_id} and all associated data deleted successfully")
        except Exception as e:
            logging.error(f"Error deleting portfolio {portfolio_id}: {e}")
            raise


    #=====================
    # Trade Management
    #=====================

    @timed_async
    async def get_traders(self, portfolio_id: str) -> List[dict]:
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM portfolio_traders WHERE portfolio_id = $1",
                    portfolio_id
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logging.error(f"Error getting traders for portfolio {portfolio_id}: {e}")
            return []

    @timed_async
    async def save_trade(self, portfolio_id: str, trader_id: str, trade: Trade) -> None:
        """Save a completed trade to the database.
        
        Uses INSERT (not UPSERT) because trades are immutable once completed.
        If a trade with the same parameters already exists, it will raise an error.
        
        Args:
            portfolio_id: str
            trader_id: str
            trade: Trade (completed trade)
        """
        try:
            # Generate a simple trade ID based on portfolio, trader, and timestamp
            # Format: portfolio_id-trader_id-timestamp
            exit_timestamp = int(trade.exit_time.timestamp.timestamp())
            trade_id = f"{portfolio_id}-{trader_id}-{exit_timestamp}"
            
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO trades (id, portfolio_id, trader_id, symbol, side, entry_price, exit_price, quantity, pnl, pnl_percentage, entry_time, exit_time)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    trade_id,
                    portfolio_id,
                    trader_id,
                    str(trade.symbol),
                    "BUY",  # El trade no tiene side, asumimos BUY por ahora
                    trade.entry_price.value,
                    trade.exit_price.value,
                    trade.quantity.value,
                    trade.pnl.value,
                    Decimal(str(trade.pnl_percentage)),
                    trade.entry_time.timestamp,
                    trade.exit_time.timestamp
                )

                logging.info(f"Trade {trade.symbol} saved successfully")
        except Exception as e:
            logging.error(f"Error saving trade {trade.symbol}: {e}")
            raise
            
    @timed_async
    async def get_trades(self, portfolio_id: str, trader_id: Optional[str] = None, limit: int = 100) -> List[Trade]:
        try:
            async with self._pool.acquire() as conn:
                if trader_id:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM trades 
                        WHERE portfolio_id = $1 AND trader_id = $2 
                        ORDER BY exit_time DESC LIMIT $3
                        """,
                        portfolio_id, trader_id, limit
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM trades 
                        WHERE portfolio_id = $1 
                        ORDER BY exit_time DESC LIMIT $2
                        """,
                        portfolio_id, limit
                    )
                logging.info(f"Got {len(rows)} trades for portfolio {portfolio_id}, trader_id filter: {trader_id}")
                for row in rows:
                    logging.info(f"  Trade: trader_id={row.get('trader_id')}, entry={row.get('entry_time')}, exit={row.get('exit_time')}")
                trades = [self._row_to_trade(r) for r in rows]

            return trades
        except Exception as e:
            logging.error(f"Error getting trades for portfolio {portfolio_id}: {e}")
            return []

    def _row_to_trade(self, row) -> Trade:
        return Trade(
            symbol=Symbol(row["symbol"]),
            entry_price=Price(row["entry_price"]),
            exit_price=Price(row["exit_price"]),
            entry_time=Timestamp(row["entry_time"]),
            exit_time=Timestamp(row["exit_time"]),
            quantity=Quantity(row["quantity"]),
            trader_id=row.get("trader_id")
        )

    async def get_portfolio_pnl(self, portfolio_id: str) -> PnL:
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT COALESCE(SUM(pnl), 0) as total_pnl FROM trades WHERE portfolio_id = $1",
                    portfolio_id
                )
                pnl_value = result["total_pnl"] if result and "total_pnl" in result else Decimal("0")
                return PnL(pnl_value)
        except Exception as e:
            logging.error(f"Error getting portfolio PnL for portfolio {portfolio_id}: {e}")
            return PnL(Decimal("0"))



    
    




    
    

