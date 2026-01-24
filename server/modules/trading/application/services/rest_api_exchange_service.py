from modules.trading.domain.ports import ExchangePort
from modules.trading.domain.value_objects import Symbol, Interval, Timestamp
from modules.trading.domain.entities import Candle_static


class RestApiExchangeService:
    """Service for the REST API of the exchange"""

    def __init__(self, exchange_port: ExchangePort) -> None:
        self.exchange_port = exchange_port

    async def connect(self) -> None:
        """
        Connect to the exchange
        """
        await self.exchange_port.connect()

    async def disconnect(self) -> None:
        """
        Disconnect from the exchange
        """
        await self.exchange_port.disconnect()

    async def __aenter__(self) -> "RestApiExchangeService":
        """
        Enter the context manager
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Exit the context manager
        """
        await self.disconnect()

    async def get_historical_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        """
        Get historical candles from the exchange
        Args:
            symbol: Symbol to get candles for
            interval: Interval to get candles for
            limit: Limit of candles to get
        Returns:
            list[Candle_static]: List of candles that are closed
        """
        return await self.exchange_port.get_historical_candles(symbol, interval, limit)

    async def get_candles_since(self, symbol: Symbol, interval: Interval, start_time: Timestamp) -> list[Candle_static]:
        """
        Get candles from start_time until now
        Args:
            symbol: Symbol to get candles for
            interval: Interval to get candles for
            start_time: Start time to get candles from
        Returns:
            list[Candle_static]: List of candles that are closed
        """
        return await self.exchange_port.get_candles_since(symbol, interval, start_time)