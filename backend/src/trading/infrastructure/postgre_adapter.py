from trading.domain.ports import StoragePort
from trading.domain.entities import Candle
from trading.domain.value_objects import Symbol, TimeFrame, Candle_static, Timestamp, Price, Quantity
import asyncpg
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

class PostgreAdapter(StoragePort):
    """Adapter for the Postgres database"""

    def __init__(self, db_url: str) -> None:
        """Initialize the Postgres adapter"""
        self.db_url = db_url
        self._pool: asyncpg.Pool | None = None

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=15))
    async def connect(self) -> None:
        """Connect to the Postgres database"""
        self._pool = await asyncpg.create_pool(self.db_url)
        logging.info("Connected to the Postgres database")

    async def disconnect(self) -> None:
        """Disconnect from the Postgres database"""
        if self._pool:
            await self._pool.close()
        self._pool = None
        logging.info("Disconnected from the Postgres database")

    async def __aenter__(self):
        """Enter the context manager"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager"""
        await self.disconnect()

    async def save_candles(self, candles: list[Candle_static]) -> None   :
        """Save a candle to the database"""
        logging.info(f"Saving candles: {Candle_static._print_table(candles)}")
        if not self._pool:
            raise ValueError("Database not connected")

        candles_to_insert = [(str(c.symbol),
                c.interval.value,
                c.timestamp.timestamp,
                c.open.value,
                c.high.value,
                c.low.value,
                c.close.value,
                c.volume.value) for c in candles]

        try:
            async with self._pool.acquire() as connection:
                await connection.executemany(
                    """
                INSERT INTO candles (symbol, interval, open_time, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (symbol, interval, open_time) DO NOTHING
                """,
                candles_to_insert
            )
        except Exception as e:
            logging.error(f"Error saving candles: {e}")
            raise

    async def get_candles(self, symbol: Symbol, interval: TimeFrame, limit: int) -> list[Candle_static]:
        """Get candles for a symbol and interval"""
        if not self._pool:
            raise ValueError("Database not connected")
        
        try:
            async with self._pool.acquire() as connection:
                result = await connection.fetch(
                    """
                    SELECT * FROM candles
                    WHERE symbol = $1 AND interval = $2
                    ORDER BY open_time DESC
                    LIMIT $3
                    """,
                    str(symbol), interval.value, limit)
                logging.info(f"Got {len(result)} {symbol} {interval} candles")
                return [self._convert_to_candle_static(row) for row in result]

        except Exception as e:
            logging.error(f"Error getting candles: {e}")
            raise
        

    def _convert_to_candle_static(self, row: dict) -> Candle_static:
        return Candle_static(
            symbol=Symbol(row["symbol"]),
            interval=TimeFrame(row["interval"]),
            timestamp=Timestamp(row["open_time"]),
            open=Price(row["open"]),
            high=Price(row["high"]),
            low=Price(row["low"]),
            close=Price(row["close"]),
            volume=Quantity(row["volume"]),
        )


    async def get_last_candle(self, symbol: Symbol, interval: TimeFrame) -> Candle_static:
        """Get the last candle for a symbol and interval"""
        if not self._pool:
            raise ValueError("Database not connected")
        
        try:
            async with self._pool.acquire() as connection:
                result = await connection.fetchrow(
                    """
                    SELECT * FROM candles
                    WHERE symbol = $1 AND interval = $2
                    ORDER BY open_time DESC
                    LIMIT 1
                    """,
                    str(symbol), interval.value)

                if result:
                    return self._convert_to_candle_static(result)
                else:
                    return None

        except Exception as e:
            logging.error(f"Error getting last candle: {e}")
            raise
                             

    async def delete_candles(self, symbol: Symbol, interval: TimeFrame, limit: int | None = None) -> int:
        """Delete candles for a symbol and interval"""
        if not self._pool:
            raise ValueError("Database not connected")
        
        async with self._pool.acquire() as connection:
            if limit:
                # Borrar solo las N más antiguas
                result = await connection.execute(
                    """
                    DELETE FROM candles
                    WHERE id IN (
                        SELECT id FROM candles
                        WHERE symbol = $1 AND interval = $2
                        ORDER BY open_time ASC
                        LIMIT $3
                    )
                    """,
                    str(symbol),
                    interval.value,
                    limit
                )
            else:
                # Borrar todas
                result = await connection.execute(
                    """
                    DELETE FROM candles
                    WHERE symbol = $1 AND interval = $2
                    """,
                    str(symbol),
                    interval.value
                )
            
            # result = "DELETE 5" -> extraer el número
            return int(result.split()[-1])


    
    async def count_candles(self, symbol: Symbol, interval: TimeFrame) -> int:
        """Count the number of candles for a symbol and interval"""
        if not self._pool:
            raise ValueError("Database nor connected")
        
        try:
            async with self._pool.acquire() as connection:
                result = await connection.fetchval(
                    """
                    SELECT COUNT(*) FROM candles
                    WHERE symbol = $1 AND interval = $2
                    """,
                    str(symbol),
                    interval.value
                )

                return result
        
        except Exception as e:
            logging.error(f"Error counting candles: {e}")
            raise 
            

