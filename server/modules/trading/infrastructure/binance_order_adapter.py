"""
Binance Order Adapter - Executes MARKET orders via REST API.

Uses Binance Testnet for paper trading.
Testnet URL: https://testnet.binance.vision

API Keys:
  - Set in .env file as BINANCE_API_KEY and BINANCE_SECRET_KEY
  
"""
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from dotenv import load_dotenv
from binance import AsyncClient
from binance.enums import ORDER_TYPE_MARKET
from pathlib import Path
from ..domain.utils.metaclasses import AdapterMeta
from ..domain.ports import OrderPort
from ..domain.entities import OrderResponse
from ..domain.value_objects import Symbol, Price, Quantity, Timestamp, TradeStatus, Side
from ..domain.utils.decorators import timed_async

# Load .env file
env_path = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)


class BinanceOrderAdapter(OrderPort, metaclass=AdapterMeta):
    """
    Adapter for executing MARKET orders on Binance.
    
    MARKET orders execute immediately at current price.
    No WebSocket needed - simple REST calls.
    """
    
    def __init__(
        self, 
        testnet: bool = True,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None
    ) -> None:
        # Load from params, env vars, or .env (in order of priority)
        self._api_key = api_key or os.getenv("BINANCE_API_KEY")
        self._api_secret = api_secret or os.getenv("BINANCE_SECRET_KEY")
        self._testnet = testnet
        self._client: AsyncClient | None = None
        
        if not self._api_key or not self._api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_SECRET_KEY must be set in .env")

    async def connect(self) -> "BinanceOrderAdapter":
        """Connect to Binance API."""
        self._client = await AsyncClient.create(
            api_key=self._api_key,
            api_secret=self._api_secret,
            testnet=self._testnet
        )
        logger.info(f"Connected to Binance {'Testnet' if self._testnet else 'Production'}")
        return self

    async def disconnect(self) -> None:
        """Disconnect from Binance API."""
        if self._client:
            await self._client.close_connection()
            self._client = None
            logger.info("Disconnected from Binance")

    @timed_async
    async def buy_market(self, symbol: Symbol, quantity: Quantity) -> OrderResponse:
        """Buy at current market price."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        try:
            response = await self._client.create_order(
                symbol=str(symbol),
                side="BUY",
                type=ORDER_TYPE_MARKET,
                quantity=str(quantity.value)
            )
            
            return self._parse_response(response, symbol, Side.BUY)

        except Exception as e:
            logger.error(f"Error buying market: {e}")
            raise

    @timed_async
    async def sell_market(self, symbol: Symbol, quantity: Quantity) -> OrderResponse:
        """Sell at current market price."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        try:
            response = await self._client.create_order(
                symbol=str(symbol),
                side="SELL",
                type=ORDER_TYPE_MARKET,
                quantity=str(quantity.value)
            )

            return self._parse_response(response, symbol, Side.SELL)

        except Exception as e:
            logger.error(f"Error selling market: {e}")
            raise

    async def cancel_order(self, symbol: Symbol, order_id: str) -> OrderResponse:
        """Cancel an open order."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        try:
            response = await self._client.cancel_order(
                symbol=str(symbol),
                orderId=order_id
            )
            
            return OrderResponse(
                order_id=str(response["orderId"]),
                symbol=symbol,
                quantity=Quantity(Decimal(response["origQty"])),
                price=Price(Decimal(response["price"]) or Decimal("0.01")),
                side=Side.BUY if response["side"] == "BUY" else Side.SELL,
                status=TradeStatus.CANCELLED,
                timestamp=Timestamp(datetime.now(timezone.utc))
            )
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise

    async def get_balance(self, asset: str) -> Price:
        """Get available balance for an asset (e.g., 'USDT', 'BTC')."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        try:
            account = await self._client.get_account()
            
            for balance in account["balances"]:
                if balance["asset"] == asset:
                    free = Decimal(balance["free"])
                    return Price(free) if free > 0 else Price(Decimal("0.01"))
            
            raise ValueError(f"Asset {asset} not found")
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            raise

    async def get_current_price(self, symbol: Symbol) -> Price:
        """Get current market price for a symbol."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        try:
            ticker = await self._client.get_symbol_ticker(symbol=str(symbol))
            return Price(Decimal(ticker["price"]))
            
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            raise

    def _parse_response(self, response: dict, symbol: Symbol, side: Side) -> OrderResponse:
        """Parse Binance order response."""
        # MARKET orders: calculate average price from fills
        fills = response.get("fills", [])
        if fills:
            total_qty = sum(Decimal(f["qty"]) for f in fills)
            total_cost = sum(Decimal(f["qty"]) * Decimal(f["price"]) for f in fills)
            avg_price = total_cost / total_qty if total_qty > 0 else Decimal("0.01")
        else:
            avg_price = Decimal(response.get("price", "0.01")) or Decimal("0.01")
        
        # Map Binance status
        status_map = {
            "NEW": TradeStatus.PENDING,
            "PARTIALLY_FILLED": TradeStatus.PARTIALLY_EXECUTED,
            "FILLED": TradeStatus.EXECUTED,
            "CANCELED": TradeStatus.CANCELLED,
            "REJECTED": TradeStatus.FAILED,
            "EXPIRED": TradeStatus.CANCELLED,
        }
        status = status_map.get(response["status"], TradeStatus.PENDING)
        
        return OrderResponse(
            order_id=str(response["orderId"]),
            symbol=symbol,
            quantity=Quantity(Decimal(response["executedQty"])),
            price=Price(avg_price),
            side=side,
            status=status,
            timestamp=Timestamp(datetime.fromtimestamp(response["transactTime"] / 1000, timezone.utc))
        )

    async def __aenter__(self) -> "BinanceOrderAdapter":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.disconnect()
