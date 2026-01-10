from ...domain.entities import Candle
from ...domain.value_objects import Symbol, Interval, Candle_static, Timestamp
from ...domain.ports import StoragePort, ExchangePort, StreamPort
from ...domain.utils import timed_async
from typing import Optional, AsyncIterator
import logging
import asyncio
from asyncio import Semaphore




class DataIngestionService:
    """
    Coordinates data ingestion from exchange and storage.
    
    Implements a rolling window strategy to maintain a fixed number of candles
    per symbol/interval, preventing unbounded database growth.
    
    """
    
    def __init__(
        self, storage: StoragePort, exchange: ExchangePort) -> None:
        """
        Initialize the ingestion service.
        
        Args:
            storage: Storage port for persistence
            exchange: Exchange port for historical data
            stream: Stream port for real-time data (optional)
            max_candles_per_symbol: Maximum candles to keep per symbol/interval.
                                   Default 1000 (safe for 7GB DB).
        """
        self._storage = storage
        self._exchange = exchange
        self._logger = logging.getLogger(__name__)
        self._connected = False

    async def startup(self) -> None:
        """
        Open connections to exchange and storage.
        Call this once at application startup.
        """
        if self._connected:
            self._logger.warning("Service already connected")
            return
        
        try:
            await self._exchange.connect()
            self._logger.info("Connected to exchange")
            await self._storage.connect()
            self._logger.info("Connected to storage")
            self._connected = True
        except Exception as e:
            self._logger.error(f"Error connecting to exchange and storage: {e}")
            raise

    async def shutdown(self) -> None:
        """
        Close connections to exchange and storage.
        Call this once at application shutdown.
        """
        if not self._connected:
            self._logger.warning("Service not connected")
            return
        try:

            await self._exchange.disconnect()
            self._logger.info("Disconnected from exchange")
            await self._storage.disconnect()
            self._logger.info("Disconnected from storage")
            self._connected = False
        except Exception as e:
            self._logger.error(f"Error disconnecting from exchange and storage: {e}")
            raise

    @timed_async
    async def ingest_historical_data(self, symbol: Symbol, interval: Interval) -> list[Candle_static]:
        """Ingest historical data from the exchange"""
        if not self._connected:
            raise RuntimeError("Service not connected. Call startup() first.")
        
        try:
            candles = await self._exchange.get_historical_candles(
                symbol, interval, limit=interval.max_candles)

            self._logger.info(f"Fetched {len(candles)} candles")
            return candles
        except Exception as e:
            self._logger.error(f"Error ingesting historical data: {e}")
            raise

    async def storage_candles(self, candles: list[Candle_static]) -> None:
        """Save candles to the database"""
        if not self._connected:
            raise RuntimeError("Service not connected. Call startup() first.")
        
        try:
            self._logger.info(f"Saving {len(candles)} candles to database")
            
            await self._storage.save_candles(candles)
            self._logger.info(f"Successfully saved {len(candles)} candles")
        except Exception as e:
            self._logger.error(f"Error storing candles: {e}")
            raise

    async def check_number_of_candles(self, symbol: Symbol, interval: Interval) -> int:
        """Get the number of candles in storage for a symbol/interval"""
        if not self._connected:
            raise RuntimeError("Service not connected. Call startup() first.")
        
        try:
            count = await self._storage.count_candles(symbol, interval)
            return count

        except Exception as e:
            self._logger.error(f"Error checking number of candles: {e}")
            raise

    async def maintain_rolling_window(self, symbol: Symbol, interval: Interval) -> None:
        """Delete oldest candles if count exceeds max_candles_per_symbol"""
        if not self._connected:
            raise RuntimeError("Service not connected. Call startup() first.")
        
        try:
            current_count = await self.check_number_of_candles(symbol, interval)
            max_candles = interval.max_candles
            
            if current_count > max_candles:
                excess = current_count - max_candles
                deleted = await self._storage.delete_candles(symbol, interval, limit=excess)
                self._logger.info(
                    f"Rolling window: deleted {deleted} oldest candles for "
                    f"{symbol} {interval.value} (maintaining {max_candles})"
                )
        except Exception as e:
            self._logger.error(f"Error maintaining rolling window: {e}")
            raise

    async def full_ingestion(self, symbol: Symbol, interval: Interval) -> None:
        """Run the ingestion service"""
        if not self._connected:
            raise RuntimeError("Service not connected. Call startup() first.")
        
        try:
            
                # Fetch and save historical data
            candles = await self.ingest_historical_data(symbol, interval)
            await self.storage_candles(candles)
            
            # Maintain rolling window (delete excess if any)
            await self.maintain_rolling_window(symbol, interval)
            
            self._logger.info(f"Completed ingestion for {symbol} {interval.value}")
        
        except Exception as e:
            self._logger.error(f"Error running ingestion service: {e}")
            raise

    async def sync_data(self, symbol: Symbol, interval: Interval) -> None:
        """Download only new candles from the exchange"""
        if not self._connected:
            raise RuntimeError("Service not connected. Call startup() first.")
        
        last_candle = await self._storage.get_last_candle(symbol, interval)

        try:
            if last_candle is None:
                self._logger.info(f"No candles found in storage for {symbol} {interval.value}. Running full ingestion.")
                await self.full_ingestion(symbol, interval)
                return
            
            last_time = last_candle.timestamp
            new_candles = await self._exchange.get_candles_since(symbol, interval, last_time)
            if new_candles:
                await self.storage_candles(new_candles)
                await self.maintain_rolling_window(symbol, interval)
                self._logger.info(f"Completed syncing data for {symbol} {interval.value}")
            else:
                self._logger.info(f"No new candles found for {symbol} {interval.value}")
        except Exception as e:
            self._logger.error(f"Error syncing data: {e}")
            raise

    async def sync_all(self, symbols: list[Symbol], intervals: list[Interval], max_concurrent: int = 10) -> None:
        """Sync multiple symbols/intervals with concurrency limit"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def _sync_with_limit(symbol: Symbol, interval: Interval) -> None:
            async with semaphore:
                await self.sync_data(symbol, interval)

        tasks =  [_sync_with_limit(symbol, interval) for symbol in symbols for interval in intervals]
        
        await asyncio.gather(*tasks)
        self._logger.info(f"Completed syncing {len(tasks)} symbol/interval pairs")



    async def __aenter__(self) -> "DataIngestionService":
        """Async context manager entry"""
        await self.startup()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Async context manager exit"""
        await self.shutdown()
