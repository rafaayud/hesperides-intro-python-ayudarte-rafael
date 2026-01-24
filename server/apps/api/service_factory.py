from modules.trading.domain.ports import ExchangePort, StoragePort, StreamPort, OrderPort
from modules.trading.application.services.ingestion_service import DataIngestionService
from modules.trading.application.services.rest_api_exchange_service import RestApiExchangeService
from modules.trading.application.services.streaming_service import StreamingService
from modules.trading.application.services.data_storage_service import DataStorageService
from modules.trading.application.services.trading_engine import TradingEngine
from .config import Settings
from .registry import AdapterRegistry

class ServiceFactory:
    """Factory for creating services, injecting dependencies"""

    def __init__(self, registry: AdapterRegistry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings


    def create_ingestion_service(self, storage: str | None = None, exchange: str | None = None) -> DataIngestionService:
        """
        Create a data ingestion service
        Args:
            storage: Storage to use
            exchange: Exchange to use
        Returns:
            DataIngestionService: Data ingestion service
        """
        if storage is None:
            storage = self.settings.default_storage
        if exchange is None:
            exchange = self.settings.default_exchange

        return DataIngestionService(
            storage=self.registry.get_storage(storage, database_url=self.settings.database_url),
            exchange=self.registry.get_exchange(exchange)
        )

    def create_data_storage_service(self, storage: str | None = None) -> DataStorageService:
        """
        Create a data storage service
        Args:
            storage: Storage to use
        Returns:
            DataStorageService: Data storage service
        """
        if storage is None:
            storage = self.settings.default_storage

        return DataStorageService(
            storage_port=self.registry.get_storage(storage, database_url=self.settings.database_url)
        )

    def create_rest_api_exchange_service(self, exchange: str | None = None) -> RestApiExchangeService:
        """
        Create a REST API exchange service
        Args:
            exchange: Exchange to use
        Returns:
            RestApiExchangeService: REST API exchange service
        """
        if exchange is None:
            exchange = self.settings.default_exchange

        return RestApiExchangeService(
            exchange_port=self.registry.get_exchange(exchange)
        )

    def create_streaming_service(self, exchange: str | None = None) -> StreamingService:
        """
        Create a streaming service
        Args:
            exchange: Exchange to use
        Returns:
            StreamingService: Streaming service
        """
        if exchange is None:
            exchange = self.settings.default_exchange

        return StreamingService(
            stream_port=self.registry.get_stream(exchange))

    def create_trading_engine(self, exchange: str | None = None, stream: str | None = None, order: str | None = None, portfolio_storage: str | None = None) -> TradingEngine:
        """
        Create a trading service
        Args:
            exchange: Exchange to use
            stream: Stream to use
            order: Order to use
            portfolio_storage: Portfolio storage to use
        Returns:
            TradingEngine: Trading engine
        """
        if exchange is None:
            exchange = self.settings.default_exchange
        
        if stream is None:
            stream = self.settings.default_stream
        
        if order is None:
            order = self.settings.default_order
        
        if portfolio_storage is None:
            portfolio_storage = self.settings.default_portfolio_storage

        return TradingEngine(
            exchange=self.registry.get_exchange(exchange),
            stream=self.registry.get_stream(stream),
            order=self.registry.get_order(order),
            portfolio_storage=self.registry.get_portfolio_storage(portfolio_storage, database_url=self.settings.database_url)
        )
        



