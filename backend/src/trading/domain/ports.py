from abc import ABC, abstractmethod
from typing import AsyncIterator
from .value_objects import Symbol, Price, Interval, Candle_static, Timestamp, TradeStatus, Quantity
from .entities import Candle, Order, OrderResponse

"""The ports are the interfaces that the application uses to interact with the external world. Here we
define the interfaces for the exchange, the database and the trading engine."""

class ExchangePort(ABC):
    """Port for the exchange"""
    @abstractmethod
    async def connect(self) -> "ExchangePort":
        """Connect to the exchange"""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange"""
    
    @abstractmethod
    async def get_historical_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        """Get candles from the exchange from now until limit candles ago"""
        
    @abstractmethod
    async def get_candles_since(self, symbol: Symbol, interval: Interval, start_time: Timestamp) -> list[Candle_static]:
        """Get candles from start_time until now"""

class StreamPort(ABC):
    """Port for the exchange using a socket"""
    @abstractmethod
    async def connect(self) -> "StreamPort":
        """Connect to the exchange"""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange"""
    
    @abstractmethod
    async def get_live_candle(self, symbol: Symbol, interval: Interval) -> Candle:
        """Get the live candle from the exchange"""

    @abstractmethod
    async def stream_candle(self, symbol: Symbol, interval: Interval) -> AsyncIterator[Candle]:
        """Stream a candle from the exchange"""

class StoragePort(ABC):
    """Port for the Postgres database"""
    @abstractmethod
    async def connect(self) -> "StoragePort":
        """Connect to the database"""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the database"""
    
    @abstractmethod
    async def save_candles(self, candles: list[Candle_static]) -> None:
        """Save candles to the database"""
    
    @abstractmethod
    async def get_candles(self, symbol: Symbol, interval: Interval, limit: int) -> list[Candle_static]:
        """Get candles from the database"""

    @abstractmethod
    async def get_last_candle(self, symbol: Symbol, interval: Interval) -> Candle_static:
        """Get the last candle from the database"""
    
    @abstractmethod
    async def delete_candles(self, symbol: Symbol, interval: Interval, limit: int) -> int:
        """Delete candles from the database"""

    @abstractmethod
    async def count_candles(self, symbol: Symbol, interval: Interval) -> int:
        """Count the number of candles in the database"""
    

class OrderPort(ABC):
    """
    Port for order execution via REST API.
    
    Simple trading: MARKET orders only (execute at current price).
    When signal fires, use all available capital to buy/sell.
    """

    @abstractmethod
    async def connect(self) -> "OrderPort":
        """Connect to the exchange API."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the exchange API."""

    @abstractmethod
    async def buy_market(self, symbol: Symbol, quantity: Quantity) -> OrderResponse:
        """
        Buy at current market price.
        Uses all the quantity specified.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            quantity: Amount to buy
            
        Returns:
            OrderResponse with the status of the order
        """

    @abstractmethod
    async def sell_market(self, symbol: Symbol, quantity: Quantity) -> OrderResponse:
        """
        Sell at current market price.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            quantity: Amount to sell
            
        Returns:
            OrderResponse with the status of the order
        """

    @abstractmethod
    async def get_balance(self, asset: str) -> Price:
        """
        Get available balance for an asset.
        
        Args:
            asset: Asset symbol (e.g., "USDT", "BTC")
            
        Returns:
            Available balance as Price
        """

    @abstractmethod
    async def get_current_price(self, symbol: Symbol) -> Price:
        """
        Get current market price.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            
        Returns:
            Current price
        """

    @abstractmethod
    async def cancel_order(self, symbol: Symbol, order_id: str) -> OrderResponse:
        """Cancel an order.
        
        Args:
            symbol: Trading pair
            order_id: ID of the order to cancel
            
        Returns:
            OrderResponse with cancellation status
        """
