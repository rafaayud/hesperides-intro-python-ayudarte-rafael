from ...domain.ports import OrderPort
from ...domain.entities import OrderResponse
from ...domain.value_objects import Symbol, Price, Quantity, Timestamp, TradeStatus, Side
from decimal import Decimal
from datetime import datetime, timezone
import random
from ...domain.utils.metaclasses import AdapterMeta


class MockOrderAdapter(OrderPort, metaclass=AdapterMeta):
    """
    Mock order adapter that simulates order execution with partial fills.
    
    Simulates:
    - Slippage (price variation)
    - Commission
    - Multiple fills per order
    - Balance tracking
    - Current price tracking
    """
    
    def __init__(
        self, 
        slippage: float = 0.001,  # 0.1% price slippage
        commission_rate: float = 0.001,  # 0.1% commission
        min_fills: int = 1,
        max_fills: int = 3,
        seed: int | None = None,
        initial_balance: dict[str, Decimal] = None
    ):
        self._slippage = slippage
        self._commission_rate = commission_rate
        self._min_fills = min_fills
        self._max_fills = max_fills
        self._orders: dict[str, dict] = {}
        self._next_order_id = 1
        
        # Mock balances (default: 10000 USDT)
        self._balances: dict[str, Decimal] = initial_balance or {"USDT": Decimal("10000")}
        
        # Mock prices (default: BTCUSDT = 45000)
        self._prices: dict[str, Decimal] = {"BTCUSDT": Decimal("45000")}
        
        if seed is not None:
            random.seed(seed)
    
    async def connect(self) -> "OrderPort":
        """Connect to the exchange API."""
        return self
    
    async def disconnect(self) -> None:
        """Disconnect from the exchange API."""
        pass
    
    async def buy_market(self, symbol: Symbol, quantity: Quantity) -> OrderResponse:
        """
        Buy at current market price with simulated fills.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            quantity: Amount to buy
            
        Returns:
            OrderResponse with the status of the order
        """
        order_id = str(self._next_order_id)
        self._next_order_id += 1
        
        # Get current price (with some variation)
        base_price = self._prices.get(str(symbol), Decimal("45000"))
        total_qty = quantity.value
        
        # Generate fills
        fills = []
        remaining = total_qty
        num_fills = random.randint(self._min_fills, self._max_fills)
        
        for i in range(num_fills):
            if remaining <= 0:
                break
            
            # Quantity for this fill
            if i == num_fills - 1:
                fill_qty = remaining
            else:
                fill_qty = remaining * Decimal(str(random.uniform(0.3, 0.7)))
                fill_qty = fill_qty.quantize(Decimal("0.00000001"))
            
            # Price with slippage
            slippage = Decimal(str(random.uniform(-self._slippage, self._slippage)))
            fill_price = base_price * (1 + slippage)
            
            fills.append({
                "price": str(fill_price.quantize(Decimal("0.01"))),
                "qty": str(fill_qty),
            })
            
            remaining -= fill_qty
        
        # Calculate average price
        executed_qty = sum(Decimal(f["qty"]) for f in fills)
        total_cost = sum(Decimal(f["qty"]) * Decimal(f["price"]) for f in fills)
        avg_price = total_cost / executed_qty if executed_qty > 0 else base_price
        
        # Determine status
        if executed_qty >= total_qty * Decimal("0.99"):  # 99% filled = FILLED
            status = TradeStatus.EXECUTED
        elif executed_qty > 0:
            status = TradeStatus.PARTIALLY_EXECUTED
        else:
            status = TradeStatus.FAILED
        
        # Store order
        self._orders[order_id] = {
            "orderId": order_id,
            "symbol": str(symbol),
            "side": "BUY",
            "status": status.value,
            "executedQty": str(executed_qty),
            "avgPrice": str(avg_price),
        }
        
        return OrderResponse(
            order_id=order_id,
            symbol=symbol,
            quantity=Quantity(executed_qty),
            price=Price(avg_price),
            side=Side.BUY,
            status=status,
            timestamp=Timestamp(datetime.now(timezone.utc))
        )
    
    async def sell_market(self, symbol: Symbol, quantity: Quantity) -> OrderResponse:
        """
        Sell at current market price with simulated fills.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            quantity: Amount to sell
            
        Returns:
            OrderResponse with the status of the order
        """
        order_id = str(self._next_order_id)
        self._next_order_id += 1
        
        # Get current price (with some variation)
        base_price = self._prices.get(str(symbol), Decimal("45000"))
        total_qty = quantity.value
        
        # Generate fills
        fills = []
        remaining = total_qty
        num_fills = random.randint(self._min_fills, self._max_fills)
        
        for i in range(num_fills):
            if remaining <= 0:
                break
            
            # Quantity for this fill
            if i == num_fills - 1:
                fill_qty = remaining
            else:
                fill_qty = remaining * Decimal(str(random.uniform(0.3, 0.7)))
                fill_qty = fill_qty.quantize(Decimal("0.00000001"))
            
            # Price with slippage
            slippage = Decimal(str(random.uniform(-self._slippage, self._slippage)))
            fill_price = base_price * (1 + slippage)
            
            fills.append({
                "price": str(fill_price.quantize(Decimal("0.01"))),
                "qty": str(fill_qty),
            })
            
            remaining -= fill_qty
        
        # Calculate average price
        executed_qty = sum(Decimal(f["qty"]) for f in fills)
        total_cost = sum(Decimal(f["qty"]) * Decimal(f["price"]) for f in fills)
        avg_price = total_cost / executed_qty if executed_qty > 0 else base_price
        
        # Determine status
        if executed_qty >= total_qty * Decimal("0.99"):  # 99% filled = FILLED
            status = TradeStatus.EXECUTED
        elif executed_qty > 0:
            status = TradeStatus.PARTIALLY_EXECUTED
        else:
            status = TradeStatus.FAILED
        
        # Store order
        self._orders[order_id] = {
            "orderId": order_id,
            "symbol": str(symbol),
            "side": "SELL",
            "status": status.value,
            "executedQty": str(executed_qty),
            "avgPrice": str(avg_price),
        }
        
        return OrderResponse(
            order_id=order_id,
            symbol=symbol,
            quantity=Quantity(executed_qty),
            price=Price(avg_price),
            side=Side.SELL,
            status=status,
            timestamp=Timestamp(datetime.now(timezone.utc))
        )
    
    async def get_balance(self, asset: str) -> Price:
        """
        Get available balance for an asset.
        
        Args:
            asset: Asset symbol (e.g., "USDT", "BTC")
            
        Returns:
            Available balance as Price
        """
        balance = self._balances.get(asset, Decimal("0"))
        return Price(balance if balance > 0 else Decimal("0.01"))
    
    async def get_current_price(self, symbol: Symbol) -> Price:
        """
        Get current market price.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            
        Returns:
            Current price
        """
        price = self._prices.get(str(symbol), Decimal("45000"))
        # Add small random variation to simulate market movement
        variation = Decimal(str(random.uniform(-0.001, 0.001)))
        current_price = price * (1 + variation)
        return Price(current_price)
    
    async def cancel_order(self, symbol: Symbol, order_id: str) -> OrderResponse:
        """
        Cancel an order.
        
        Args:
            symbol: Trading pair
            order_id: ID of the order to cancel
            
        Returns:
            OrderResponse with cancellation status
        """
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self._orders[order_id]
        order["status"] = TradeStatus.CANCELLED.value
        
        return OrderResponse(
            order_id=order_id,
            symbol=symbol,
            quantity=Quantity(Decimal(order.get("executedQty", "0"))),
            price=Price(Decimal(order.get("avgPrice", "0.01"))),
            side=Side.BUY if order["side"] == "BUY" else Side.SELL,
            status=TradeStatus.CANCELLED,
            timestamp=Timestamp(datetime.now(timezone.utc))
        )
    
    # Helper methods for testing
    def set_price(self, symbol: Symbol, price: Decimal) -> None:
        """Set mock price for a symbol."""
        self._prices[str(symbol)] = price
    
    def set_balance(self, asset: str, balance: Decimal) -> None:
        """Set mock balance for an asset."""
        self._balances[asset] = balance


# Test
if __name__ == "__main__":
    from ...domain.value_objects import Symbol, Quantity
    import asyncio
    
    async def main():
        adapter = MockOrderAdapter(min_fills=2, max_fills=4, seed=42)
        await adapter.connect()
        
        # Test buy
        symbol = Symbol("BTCUSDT")
        response = await adapter.buy_market(symbol, Quantity(Decimal("1.0")))
        
        print(f"Order ID: {response.order_id}")
        print(f"Status: {response.status.value}")
        print(f"Quantity: {response.quantity.value}")
        print(f"Price: ${response.price.value}")
        print(f"Side: {response.side.value}")
        
        # Test price
        price = await adapter.get_current_price(symbol)
        print(f"\nCurrent price: ${price.value}")
        
        # Test balance
        balance = await adapter.get_balance("USDT")
        print(f"USDT balance: ${balance.value}")
    
    asyncio.run(main())
