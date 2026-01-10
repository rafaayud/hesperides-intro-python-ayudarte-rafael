from ...domain.ports import orderPort
from ...domain.entities import Order
from ...domain.value_objects import TradeStatus
from decimal import Decimal
import random


class MockOrderAdapter(orderPort):
    """
    Mock order adapter that simulates order execution with partial fills.
    Uses simple dicts instead of extra classes.
    """
    
    def __init__(
        self,
        slippage: float = 0.001,  # 0.1% price slippage
        commission_rate: float = 0.001,  # 0.1% commission
        min_fills: int = 1,
        max_fills: int = 3,
        seed: int | None = None
    ):
        self._slippage = slippage
        self._commission_rate = commission_rate
        self._min_fills = min_fills
        self._max_fills = max_fills
        self._orders: dict[int, dict] = {}
        self._next_order_id = 1
        
        if seed is not None:
            random.seed(seed)
    
    async def send_order(self, order: Order) -> dict:
        """
        Send order and return response with fills.
        
        Returns dict like Binance API:
        {
            "symbol": "BTCUSDT",
            "orderId": 123,
            "status": "FILLED",
            "executedQty": "1.0",
            "fills": [
                {"price": "45000", "qty": "0.5", "commission": "0.0005"},
                {"price": "45010", "qty": "0.5", "commission": "0.0005"}
            ]
        }
        """
        order_id = self._next_order_id
        self._next_order_id += 1
        
        base_price = order.price.value
        total_qty = order.quantity.value
        
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
            
            # Commission
            commission = fill_qty * fill_price * Decimal(str(self._commission_rate))
            
            fills.append({
                "price": str(fill_price.quantize(Decimal("0.01"))),
                "qty": str(fill_qty),
                "commission": str(commission.quantize(Decimal("0.00000001"))),
                "commissionAsset": order.symbol.symbol.replace("USDT", "")
            })
            
            remaining -= fill_qty
        
        executed_qty = sum(Decimal(f["qty"]) for f in fills)
        
        response = {
            "symbol": order.symbol.symbol,
            "orderId": order_id,
            "clientOrderId": f"mock_{order_id}",
            "price": str(base_price),
            "origQty": str(total_qty),
            "executedQty": str(executed_qty),
            "status": "FILLED" if executed_qty >= total_qty else "PARTIALLY_FILLED",
            "type": "LIMIT",
            "side": order.side.value,
            "fills": fills
        }
        
        self._orders[order_id] = response
        return response
    
    async def cancel_order(self, order_id: str) -> None:
        oid = int(order_id)
        if oid in self._orders:
            self._orders[oid]["status"] = "CANCELED"
    
    @property
    def order_status(self, order_id: str) -> TradeStatus:
        oid = int(order_id)
        if oid not in self._orders:
            return TradeStatus.PENDING
        
        status_map = {
            "NEW": TradeStatus.PENDING,
            "PARTIALLY_FILLED": TradeStatus.PARTIALLY_EXECUTED,
            "FILLED": TradeStatus.EXECUTED,
            "CANCELED": TradeStatus.CANCELED
        }
        return status_map.get(self._orders[oid]["status"], TradeStatus.PENDING)
    
    def get_order(self, order_id: int) -> dict | None:
        return self._orders.get(order_id)


# Test
if __name__ == "__main__":
    from trading.domain.value_objects import Symbol, Price, Quantity, Timestamp, Side
    from datetime import datetime
    import asyncio
    
    async def main():
        adapter = MockOrderAdapter(min_fills=2, max_fills=4, seed=42)
        
        order = Order(
            order_id="test",
            symbol=Symbol("BTCUSDT"),
            quantity=Quantity(Decimal("1.0")),
            price=Price(Decimal("45000.00")),
            side=Side.BUY,
            status=TradeStatus.PENDING,
            timestamp=Timestamp(datetime.now()),
            execution_id=""
        )
        
        response = await adapter.send_order(order)
        
        print(f"Order ID: {response['orderId']}")
        print(f"Status: {response['status']}")
        print(f"Executed: {response['executedQty']} / {response['origQty']}")
        print(f"\nFills ({len(response['fills'])}):")
        
        for i, fill in enumerate(response['fills'], 1):
            print(f"  {i}. Price: ${fill['price']}, Qty: {fill['qty']}, Commission: {fill['commission']} {fill['commissionAsset']}")
    
    asyncio.run(main())
