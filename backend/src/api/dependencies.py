from typing import Type, Callable
from ..trading.domain.ports import ExchangePort, StoragePort, StreamPort, OrderPort
from .config import Settings

class AdapterRegistry:
    """Registry of adapters for the API"""
    

    # A disctionary that returns a callable that generates an adapter so I do not have the adapter saved all the time I call it when I need it.
    _exchanges: dict[str, Callable[..., ExchangePort]] = {}
    _storages: dict[str, Callable[..., StoragePort]] = {}
    _streams: dict[str, Callable[..., StreamPort]] = {}
    _orders: dict[str, Callable[..., OrderPort]] = {}


    #=========== REGISTER ADAPTERS ===========
    @classmethod
    def register_exchange(cls, name: str, adapter: Callable[..., ExchangePort]) -> None:
        cls._exchanges[name] = adapter

    @classmethod
    def register_storage(cls, name: str, adapter: Callable[..., StoragePort]) -> None:
        cls._storages[name] = adapter

    @classmethod
    def register_stream(cls, name: str, adapter: Callable[..., StreamPort]) -> None:
        cls._streams[name] = adapter

    @classmethod
    def register_order(cls, name: str, adapter: Callable[..., OrderPort]) -> None:
        cls._orders[name] = adapter

    #=========== GET ADAPTERS ===========
    @classmethod
    def get_exchange(cls, name: str) -> ExchangePort:
        return cls._exchanges[name]()
    
    @classmethod
    def get_storage(cls, name: str, **kwargs) -> StoragePort:
        return cls._storages[name](**kwargs)
    
    @classmethod
    def get_stream(cls, name: str) -> StreamPort:
        return cls._streams[name]()
    
    @classmethod
    def get_order(cls, name: str) -> OrderPort:
        return cls._orders[name]()



def setup_registry(settings: Settings) -> None:
    from ..trading.infrastructure.binance_adapter import BinanceAdapter
    from ..trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter
    from ..trading.infrastructure.postgre_adapter import PostgresAdapter
    from ..trading.infrastructure.binance_order_adapter import BinanceOrderAdapter

    from ..trading.infrastructure.mocks.mock_storage_adapter import MockStorageAdapter
    from ..trading.infrastructure.mocks.mock_stream_adapter import MockStreamAdapter
    from ..trading.infrastructure.mocks.mock_exchange_adapter import MockExchangeAdapter
    from ..trading.infrastructure.mocks.mock_order_adapter import MockOrderAdapter

    AdapterRegistry.register_exchange("binance", BinanceAdapter)
    AdapterRegistry.register_stream("binance", BinanceStreamAdapter)
    AdapterRegistry.register_storage("postgres", lambda database_url=settings.database_url: PostgresAdapter(database_url))
    AdapterRegistry.register_stream("binance", BinanceStreamAdapter)

    AdapterRegistry.register_storage("mock", MockStorageAdapter)
    AdapterRegistry.register_stream("mock", MockStreamAdapter)
    AdapterRegistry.register_exchange("mock", MockExchangeAdapter)
    AdapterRegistry.register_order("mock", MockOrderAdapter)

