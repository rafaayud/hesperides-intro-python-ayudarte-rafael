from typing import Callable
from modules.trading.domain.ports import ExchangePort, StoragePort, StreamPort, OrderPort, PortfolioStoragePort


class AdapterRegistry:
    """Registry of adapters for the API"""
    

    # A dictionary that returns a callable that generates an adapter so I do not have the adapter saved all the time I call it when I need it.
    _exchanges: dict[str, Callable[..., ExchangePort]] = {}
    _storages: dict[str, Callable[..., StoragePort]] = {}
    _streams: dict[str, Callable[..., StreamPort]] = {}
    _orders: dict[str, Callable[..., OrderPort]] = {}
    _portfolio_storages: dict[str, Callable[..., PortfolioStoragePort]] = {}

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
    
    @classmethod
    def register_portfolio_storage(cls, name: str, adapter: Callable[..., PortfolioStoragePort]) -> None:
        cls._portfolio_storages[name] = adapter

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

    @classmethod
    def get_portfolio_storage(cls, name: str, **kwargs) -> PortfolioStoragePort:
        return cls._portfolio_storages[name](**kwargs)
