"""
Test Binance Order Adapter with Testnet.

Before running:
1. Create a Testnet account at https://testnet.binance.vision/
2. Generate API keys
3. Create .env file in backend/ with:
   BINANCE_API_KEY=your_testnet_api_key
   BINANCE_API_SECRET=your_testnet_api_secret
"""
import asyncio
import logging
import sys
from pathlib import Path
from decimal import Decimal



from src.trading.infrastructure.binance_order_adapter import BinanceOrderAdapter
from src.trading.domain.value_objects import Symbol, Quantity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def test_connection_and_balance():
    """Test basic connection and balance retrieval."""
    print("\n" + "="*60)
    print("TEST 1: Connection and Balance")
    print("="*60)
    
    async with BinanceOrderAdapter(testnet=True) as broker:
        # Get USDT balance
        usdt_balance = await broker.get_balance("USDT")
        print(f"✓ USDT Balance: {usdt_balance}")
        
        # Get BTC balance
        btc_balance = await broker.get_balance("BTC")
        print(f"✓ BTC Balance: {btc_balance}")
        
        return usdt_balance


async def test_get_price():
    """Test getting current price."""
    print("\n" + "="*60)
    print("TEST 2: Get Current Price")
    print("="*60)
    
    async with BinanceOrderAdapter(testnet=True) as broker:
        symbol = Symbol("BTCUSDT")
        price = await broker.get_current_price(symbol)
        print(f"✓ {symbol} Price: ${price}")
        
        return price


async def test_small_buy_order():
    """Test a small market buy order."""
    print("\n" + "="*60)
    print("TEST 3: Small Market BUY Order")
    print("="*60)
    
    async with BinanceOrderAdapter(testnet=True) as broker:
        symbol = Symbol("BTCUSDT")
        
        # Get current price
        price = await broker.get_current_price(symbol)
        print(f"Current price: ${price}")
        
        # Buy a very small amount (0.001 BTC ≈ $45 at current prices)
        quantity = Quantity(Decimal("0.001"))
        print(f"Buying {quantity} BTC...")
        
        order = await broker.buy_market(symbol, quantity)
        print(f"✓ Order executed: {order}")
        
        return order


async def test_small_sell_order():
    """Test a small market sell order."""
    print("\n" + "="*60)
    print("TEST 4: Small Market SELL Order")
    print("="*60)
    
    async with BinanceOrderAdapter(testnet=True) as broker:
        symbol = Symbol("BTCUSDT")
        
        # Sell the same amount we bought
        quantity = Quantity(Decimal("0.001"))
        print(f"Selling {quantity} BTC...")
        
        order = await broker.sell_market(symbol, quantity)
        print(f"✓ Order executed: {order}")
        
        return order


async def test_full_flow():
    """Test complete buy/sell flow with all capital."""
    print("\n" + "="*60)
    print("TEST 5: Full Trading Flow (Buy all → Sell all)")
    print("="*60)
    
    async with BinanceOrderAdapter(testnet=True) as broker:
        symbol = Symbol("BTCUSDT")
        
        # 1. Check initial balance
        usdt_before = await broker.get_balance("USDT")
        print(f"Initial USDT: {usdt_before}")
        
        # 2. Get price
        price = await broker.get_current_price(symbol)
        print(f"BTC Price: ${price}")
        
        # 3. Calculate how much BTC we can buy (use 99% to account for fees)
        btc_quantity = Quantity((usdt_before.value * Decimal("0.99")) / price.value)
        # Round to 5 decimals (Binance minimum)
        btc_quantity = Quantity(btc_quantity.value.quantize(Decimal("0.00001")))
        print(f"Buying {btc_quantity} BTC...")
        
        # 4. Buy
        buy_order = await broker.buy_market(symbol, btc_quantity)
        print(f"✓ BUY: {buy_order}")
        
        # 5. Check BTC balance
        btc_balance = await broker.get_balance("BTC")
        print(f"BTC after buy: {btc_balance}")
        
        # 6. Sell all BTC
        sell_quantity = Quantity(btc_balance.value.quantize(Decimal("0.00001")))
        print(f"Selling {sell_quantity} BTC...")
        
        sell_order = await broker.sell_market(symbol, sell_quantity)
        print(f"✓ SELL: {sell_order}")
        
        # 7. Final balance
        usdt_after = await broker.get_balance("USDT")
        print(f"Final USDT: {usdt_after}")
        
        pnl = usdt_after.value - usdt_before.value
        print(f"PnL: {'+' if pnl >= 0 else ''}{pnl:.2f} USDT")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("BINANCE ORDER ADAPTER - TESTNET")
    print("="*60)
    
    try:
        # Basic tests
        await test_connection_and_balance()
        await test_get_price()
        
        # Order tests (comment out if you don't want to execute orders)
        # await test_small_buy_order()
        # await test_small_sell_order()
        
        # Full flow test (uncomment to test)
        # await test_full_flow()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

