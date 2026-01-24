from modules.trading.domain.ports import StoragePort
from modules.trading.domain.value_objects import Symbol, Interval
from modules.trading.domain.entities import Candle_static


class DataStorageService:
    """Service for the data storage"""
    def __init__(self, storage_port: StoragePort) -> None:
        self.storage_port = storage_port

    async def connect(self) -> None:
        """
        Connect to the storage
        """
        await self.storage_port.connect()

    async def disconnect(self) -> None:
        """
        Disconnect from the storage
        """
        await self.storage_port.disconnect()

    async def __aenter__(self) -> "DataStorageService":
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

    async def get_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        """
        Get candles from the storage
        Args:
            symbol: Symbol to get candles for
            interval: Interval to get candles for
            limit: Limit of candles to get
        Returns:
            list[Candle_static]: List of candles that are closed
        """
        return await self.storage_port.get_candles(symbol, interval, limit)