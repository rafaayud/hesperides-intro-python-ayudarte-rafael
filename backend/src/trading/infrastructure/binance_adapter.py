import aiohttp
import asyncio
from ..domain.ports import ExchangePort
from ..domain.value_objects import Symbol, Interval, Timestamp, Price, Quantity, Candle_static
from ..domain.entities import Candle
from ..domain.utils import AdapterMeta, timed_async
from decimal import Decimal
from typing import AsyncIterator
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .exceptions import RateLimitError, IPBannedError

BINANCE_REST_URL = "https://api.binance.com"
CANDLES_LIMIT = 10000


class BinanceAdapter(ExchangePort, metaclass=AdapterMeta):
    """Adapter for the Binance exchange"""

    def __init__(self, rest_url: str = BINANCE_REST_URL) -> None:
        """Initialize the Binance adapter"""
        self.rest_url = rest_url
        self._session: aiohttp.ClientSession | None = None
        self.running = False

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=15))
    async def connect(self) -> None:
        """Connect to the Binance exchange"""
        if self._session is None:
            try:
                self._session = aiohttp.ClientSession()
            except Exception as e:
                logging.error(f"Error connecting to the Binance exchange: {e}")
                raise e
            else:
                logging.info("Connected to the Binance exchange")
                self.running = True
                return True
    
    async def disconnect(self) -> bool:
        """Disconnect from the Binance exchange"""
        if self._session is not None:
            try:
                await self._session.close()
            except Exception as e:
                logging.error(f"Error disconnecting from the Binance exchange: {e}")
                return False
            else:
                logging.info("Disconnected from the Binance exchange")
                self.running = False
                return True

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, IPBannedError, ConnectionError, asyncio.TimeoutError))
    )
    async def _request(self, endpoint: str, params: dict) -> list | dict:
        """Make a request to the Binance exchange with error handling and retries"""
        if self._session is None:
            raise RuntimeError("Not connected to the Binance exchange")
        
        try:
            async with self._session.get(
                f"{self.rest_url}{endpoint}",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                
                elif response.status == 429:
                    logging.warning("Rate limited (429), tenacity will retry")
                    raise RateLimitError("Rate limited by Binance")
                
                elif response.status == 418:
                    logging.error("I am a teapot")
                    raise IPBannedError("IP banned by Binance")
                
                else:
                    raise ConnectionError(f"HTTP {response.status}")
                
        except asyncio.TimeoutError:
            logging.warning("Request timeout")
            raise


    @timed_async
    async def get_historical_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        """
        Get historical CLOSED candles from the Binance exchange.
        
        Note: We request limit+1 and discard the most recent candle 
        because it's usually still open (not closed).
        """
        if limit > CANDLES_LIMIT:
            logging.warning(f"Limit is greater than {CANDLES_LIMIT}, using {CANDLES_LIMIT}")
            limit = CANDLES_LIMIT

        # Request one extra to discard the open candle
        target_count = limit + 1
        all_candles: list[Candle_static] = []
        end_time = None

        while len(all_candles) < target_count:
            batch_size = min(1000, target_count - len(all_candles))

            params = {
                "symbol": str(symbol),
                "interval": interval.value,
                "limit": batch_size
            }

            if end_time:
                params["endTime"] = end_time

            data = await self._request("/api/v3/klines", params)

            if not data or isinstance(data, dict):
                logging.error(f"No data found for {symbol} {data}")
                break

            candles = [self._parse_candle(symbol, item, interval) for item in data]

            all_candles = candles + all_candles
            end_time = int(data[0][0]) - 1

            if len(candles) < batch_size:
                break

            logging.info(f"Fetched {len(candles)} candles for {symbol} {interval.value}")

        # Remove the most recent candle (it's not closed yet)
        if all_candles:
            all_candles = all_candles[:-1]
        
        return all_candles
    
    @timed_async
    async def get_candles_since(self, symbol: Symbol, interval: Interval, start_time: Timestamp) -> list[Candle_static]:
        """
        Get CLOSED candles from start_time until now.
        
        Note: Discards the most recent candle as it's usually still open.
        """
        all_candles: list[Candle_static] = []
        current_start_ms = int(start_time.timestamp.timestamp() * 1000)

        while True:
            params = {
                "symbol": str(symbol),
                "interval": interval.value,
                "startTime": current_start_ms,
                "limit": 1000
            }

            data = await self._request("/api/v3/klines", params)

            if not data or isinstance(data, dict):
                logging.error(f"No data found for {symbol} {data}")
                break

            candles = [self._parse_candle(symbol, item, interval) for item in data]
            all_candles.extend(candles)

            current_start_ms = int(data[-1][0]) + 1

            if len(candles) < 1000:
                break

            logging.info(f"Fetched {len(candles)} candles for {symbol} {interval.value} since {start_time}")

        # Remove the most recent candle (it's not closed yet)
        if all_candles:
            all_candles = all_candles[:-1]

        return all_candles
            
        
    
    def _parse_candle(self, symbol: Symbol, raw: list, interval: Interval) -> Candle_static:
        
        return Candle_static(
            symbol=symbol,
            timestamp=Timestamp(datetime.fromtimestamp(int(raw[0])/1000)),
            open=Price(Decimal(raw[1])),
            high=Price(Decimal(raw[2])),
            low=Price(Decimal(raw[3])),
            close=Price(Decimal(raw[4])),
            volume=Quantity(Decimal(raw[5])),
            interval= interval
        )

    async def __aenter__(self):
        """Enter the context manager"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager"""
        await self.disconnect()
    


class MockBinanceAdapter(ExchangePort):
    """Mock adapter for the Binance exchange"""
    pass