from typing import TYPE_CHECKING
from .config import Settings
from fastapi import Request, WebSocket
from .registry import AdapterRegistry

if TYPE_CHECKING:
    from .service_factory import ServiceFactory

def get_service_factory(request: Request) -> "ServiceFactory":
    """Obtiene la ServiceFactory desde app.state (para endpoints HTTP)"""
    return request.app.state.services

def get_service_factory_from_websocket(websocket: WebSocket) -> "ServiceFactory":
    """Obtiene la ServiceFactory desde app.state (para WebSockets)"""
    return websocket.app.state.services

def setup_registry(settings: Settings) -> None:
    from modules.trading.infrastructure.binance_adapter import BinanceAdapter
    from modules.trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter
    from modules.trading.infrastructure.postgre_adapter import PostgresAdapter
    from modules.trading.infrastructure.binance_order_adapter import BinanceOrderAdapter
    from modules.trading.infrastructure.postgres_portfolio_adapter import PostgresPortfolioAdapter

    from modules.trading.infrastructure.mocks.mock_storage_adapter import MockStorageAdapter
    from modules.trading.infrastructure.mocks.mock_stream_adapter import MockStreamAdapter
    from modules.trading.infrastructure.mocks.mock_exchange_adapter import MockExchangeAdapter
    from modules.trading.infrastructure.mocks.mock_order_adapter import MockOrderAdapter

    AdapterRegistry.register_exchange("binance", BinanceAdapter)
    AdapterRegistry.register_stream("binance", BinanceStreamAdapter)
    AdapterRegistry.register_storage("postgres", lambda database_url=settings.database_url: PostgresAdapter(database_url))
    AdapterRegistry.register_order("binance", BinanceOrderAdapter)
    AdapterRegistry.register_portfolio_storage("postgres", lambda database_url=settings.database_url: PostgresPortfolioAdapter(database_url))

    AdapterRegistry.register_storage("mock", MockStorageAdapter)
    AdapterRegistry.register_stream("mock", MockStreamAdapter)
    AdapterRegistry.register_exchange("mock", MockExchangeAdapter)
    AdapterRegistry.register_order("mock", MockOrderAdapter)

