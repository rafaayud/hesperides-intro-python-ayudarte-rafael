import aiohttp
import asyncio
from trading.domain.ports import ExchangePort
from trading.domain.value_objects import Symbol, TimeFrame
from trading.domain.entities import Candle
from trading.domain.value_objects import Timestamp, Price, Quantity, Candle_static
from decimal import Decimal
from typing import AsyncIterator
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .exceptions import RateLimitError, IPBannedError

BINANCE_REST_URL = "https://api.binance.com"
CANDLES_LIMIT = 10000

class BinanceAdapter(ExchangePort):
    """Adapter for the Binance exchange"""

    def __init__(self, rest_url: str = BINANCE_REST_URL, rate_limit_delay: float = 0.1) -> None:
        """Initialize the Binance adapter"""
        self.rest_url = rest_url
        self._session: aiohttp.ClientSession | None = None
        self.rate_limit_delay = rate_limit_delay
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
    stop=stop_after_attempt(5),wait=wait_exponential(multiplier=1, min=4, max=60),retry=retry_if_exception_type((RateLimitError, IPBannedError, ConnectionError, asyncio.TimeoutError)))
    async def _request(self, endpoint: str, params: dict) -> list | dict:
        """Make a request to the Binance exchange, with rate limiting and IP banning prevention"""
        if self._session is None:
            raise RuntimeError("Not connected to the Binance exchange")
        
        await asyncio.sleep(self._rate_limit_delay)  
        
        try:
            async with self._session.get(
                f"{self.rest_url}{endpoint}",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                
                elif response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    logging.warning(f"Rate limited (429), waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise RateLimitError(retry_after) 
                
                elif response.status == 418:
                    retry_after = int(response.headers.get("Retry-After", 300))
                    logging.error(f"I'm a teapot")
                    await asyncio.sleep(retry_after)
                    raise IPBannedError(retry_after)  
                
                else:
                    raise ConnectionError(f"HTTP {response.status}")
                
        except asyncio.TimeoutError:
            logging.warning("Request timeout")
            raise


    async def get_historical_candles(self, symbol: Symbol,  interval: TimeFrame, limit: int) -> list[Candle_static]:
        """Get historical candles from the Binance exchange"""


        if limit > CANDLES_LIMIT:
            logging.warning(f"Limit is greater than {CANDLES_LIMIT}, using {CANDLES_LIMIT}")
            limit = CANDLES_LIMIT

        all_candles: list[Candle_static] = []
        end_time = None

        while len(all_candles) < limit:
            batch_size = min(1000, limit - len(all_candles))

            params= {
                "symbol": str(symbol),
                "interval": interval.value,
                "limit": batch_size
            }

            if end_time:
                params["endTime"] = end_time

            async with self._session.get(f"{self.rest_url}/api/v3/klines", params=params) as response:
                data = await response.json()

            if not data:
                break

            candles = [self._parse_candle(symbol, item, interval) for item in data]

            all_candles = candles + all_candles
            end_time = int(data[0][0]) - 1

            if len(candles) < batch_size:
                break

            logging.info(f"Fetched {len(candles)} candles for {symbol} {interval.value}")

        return all_candles
    
    async def get_candles_since(self, symbol: Symbol, interval: TimeFrame, start_time: Timestamp) -> list[Candle_static]:
        """Get candles from start_time until now."""

        all_candles: list[Candle_static] = []
        current_start_ms = int(start_time.timestamp.timestamp() * 1000) 

        while True:
        
            params = {
                "symbol": str(symbol),
                "interval": interval.value,
                "startTime": current_start_ms,
                "limit": 1000
            }
            
            async with self._session.get(f"{self.rest_url}/api/v3/klines", params=params) as response:
                data = await response.json()

            if not data:
                break

            candles = [self._parse_candle(symbol, item, interval) for item in data]
            all_candles.extend(candles)

            current_start_ms = int(data[-1][0]) + 1

            if len(candles) < 1000:
                break

            logging.info(f"Fetched {len(candles)} candles for {symbol} {interval.value} since {start_time}")

        return all_candles
            
        
    
    def _parse_candle(self, symbol: Symbol, raw: list, interval: TimeFrame) -> Candle_static:
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