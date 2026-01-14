from ..trading.domain.ports import ExchangePort, StoragePort, StreamPort, OrderPort
from ..trading.application.services.ingestion_service import DataIngestionService
from ..trading.application.services.trading_engine import TradingEngine
from .dependencies import AdapterRegistry
from .config import Settings

class ServiceFactory:
    """Factory for creating services, injecting dependencies"""

    def __init__(self, registry: AdapterRegistry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings


    def create_ingestion_service(self, storage: str | None = None, exchange: str | None = None) -> DataIngestionService:
        if storage is None:
            storage = self.settings.default_storage
        if exchange is None:
            exchange = self.settings.default_exchange

        return DataIngestionService(
            storage=self.registry.get_storage(storage or self.settings.default_storage),
            exchange=self.registry.get_exchange(exchange or self.settings.default_exchange)
        )

    def create_trading_engine(self, storage: str | None = None, exchange: str | None = None) -> TradingEngine:
        pass

