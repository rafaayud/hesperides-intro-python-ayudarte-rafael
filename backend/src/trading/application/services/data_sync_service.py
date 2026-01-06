from src.trading.domain.ports import ExchangePort, StoragePort
from src.trading.domain.value_objects import Symbol, TimeFrame
from src.trading.infrastructure.binance_adapter import BinanceAdapter, PostgreAdapter
from src.trading.application.services.ingestion_service import DataIngestionService

class DataSyncService:
    def __init__(self, ingestion_service: DataIngestionService):
        self._ingestion_service = ingestion_service

    async def run(self, symbol: Symbol, timeframe: TimeFrame):
        await self._ingestion_service.sync_data(symbol, timeframe)

    async def __aenter__(self) -> "DataSyncService":
        await self._ingestion_service.startup()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._ingestion_service.shutdown()