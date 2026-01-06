from trading.domain.ports import StreamPort
from trading.domain.value_objects import Symbol, Interval, Price, Quantity, Timestamp, Candle_static
from trading.domain.entities import Candle
import asyncio
import aiohttp
import logging
import json
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator
from tenacity import retry, stop_after_attempt, wait_exponential


URL_STREAM = "wss://stream.binance.com:9443/ws"

class BinanceStreamAdapter(StreamPort):
    """Adapter that uses a socket to get the live candles from the Binance exchange"""

    def __init__(self, url_stream: str = URL_STREAM) -> None:
        self.url_stream = url_stream
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self.running = False
        self.stream_active = False
    
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=15))
    async def connect(self) -> None:
        """Connect to Binance WebSocket"""
        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()
            logging.info("WebSocket session created")
        except aiohttp.ClientError as e:
            logging.error(f"Failed to create session: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Binance WebSocket"""
        try:
            if self._ws is not None:
                await self._ws.close()
                self._ws = None
            if self._session is not None:
                await self._session.close()
                self._session = None
            self.running = False
            logging.info("WebSocket disconnected")

        except Exception as e:
            logging.error(f"Error during disconnect: {e}")

            self._ws = None
            self._session = None
            self.running = False
    
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=15))
    async def _subscribe_to_symbol(self, symbol: Symbol, interval: Interval) -> None:
        """Subscribe to a symbol and interval"""
        if self._session is None:
            raise RuntimeError("Session not created")
        
        stream = f"{str(symbol).lower()}@kline_{interval.value}"
        url = f"{self.url_stream}/{stream}"

        try:
            self._ws = await self._session.ws_connect(url, heartbeat=30, timeout=aiohttp.ClientTimeout(total=30))
            self.running = True
            logging.info(f"Subscribed to {stream}")
        
        except aiohttp.WSServerHandshakeError as e:
            logging.error(f"WebSocket handshake failed: {e}")
            raise ConnectionError(f"Could not connect to {url}")
        except asyncio.TimeoutError:
            logging.error(f"Connection timeout for {stream}")
            raise ConnectionError("WebSocket connection timeout")
        except aiohttp.ClientError as e:
            logging.error(f"Client error during subscribe: {e}")
            raise
    

    async def get_live_candle(self, symbol: Symbol, interval: Interval) -> Candle:
        """Get live candle from the Binance stream"""

        if self._ws is None:
            raise RuntimeError("Not connected to the Binance stream")

        try:
            message = await asyncio.wait_for(self._ws.receive(), timeout=60)
        except asyncio.TimeoutError:
            logging.warning("No message received in 60s")
            raise ConnectionError("WebSocket timeout - no data received")
        
        if message.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(message.data)
                return self._parse_kline(data)
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON received: {e}")
                raise ValueError(f"Could not parse message: {message.data[:100]}")
            except KeyError as e:
                logging.error(f"Missing field in kline data: {e}")
                raise ValueError(f"Malformed kline data, missing: {e}")

        elif message.type == aiohttp.WSMsgType.CLOSED:
            logging.warning("WebSocket closed by server")
            self.running = False
            raise ConnectionError("WebSocket closed by server")

        elif message.type == aiohttp.WSMsgType.ERROR:
            logging.error(f"WebSocket error: {self._ws.exception()}")
            self.running = False
            raise ConnectionError(f"WebSocket error: {self._ws.exception()}")

        else:
            logging.warning(f"Unexpected message type: {message.type}")
            raise ValueError(f"Unexpected WebSocket message type: {message.type}")

    def _parse_kline(self, data: dict) -> Candle:
        """Parse the kline data from the Binance stream"""

        k = data["k"]
        
        symbol = Symbol(k["s"])
        interval = Interval(k["i"])
        
        ohlcv = Candle_static(
            symbol=symbol,
            timestamp=Timestamp(datetime.fromtimestamp(k["t"] / 1000)),
            open=Price(Decimal(k["o"])),
            high=Price(Decimal(k["h"])),
            low=Price(Decimal(k["l"])),
            close=Price(Decimal(k["c"])),
            volume=Quantity(Decimal(k["v"])),
            interval=interval
        )
        
        return Candle(
            symbol=symbol,
            interval=interval,
            open_time=Timestamp(datetime.fromtimestamp(k["t"] / 1000)),
            close_time=Timestamp(datetime.fromtimestamp(k["T"] / 1000)),
            ohlcv=ohlcv,
            ingestion_time=Timestamp(datetime.now()),
            event_time=Timestamp(datetime.fromtimestamp(data["E"] / 1000)),
            trades_count=k["n"],
            is_closed=k["x"]
        )

    async def stream_candle(self, symbol:Symbol, interval:Interval) -> AsyncIterator[Candle]:
        """Stream the candle from the Binance stream"""
        
        try:
            await self._subscribe_to_symbol(symbol, interval)

            while self.running:
                try:
                    candle = await self.get_live_candle(symbol, interval)
                    yield candle

                except ValueError as e:
                    logging.warning(f"Skipping malformed data: {e}")
                    continue

        except ConnectionError as e:
                    logging.error(f"Connection failed after 5 retries: {e}. Resetting and retrying...")
                    await self.disconnect()
                    

    async def __aenter__(self) -> StreamPort:
        """Enter the context manager"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager"""
        await self.disconnect()

    
        
        
       
