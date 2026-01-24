from modules.trading.domain.utils import timed, timed_async
import time
import logging
import asyncio
from modules.trading.infrastructure.mocks.mock_exchange_adapter import MockExchangeAdapter
from modules.trading.domain.value_objects import Symbol, Interval


logging.basicConfig(level=logging.DEBUG)


@timed
def slow_function() -> None:
    """Simulates a slow sync function"""
    time.sleep(0.1)


async def test_async_decorator() -> None:
    """Test the timed_async decorator on mock exchange"""
    mock_exchange = MockExchangeAdapter.deterministic()
    candles = await mock_exchange.get_historical_candles(Symbol("BTCUSDT"), Interval.M1, 10)
    print(f"Got {len(candles)} candles")


if __name__ == "__main__":
    print("\n=== Testing Decorators ===\n")
    
    print("1. Testing @timed on sync function:")
    slow_function()
    
    print("\n2. Testing @timed_async on async function:")
    asyncio.run(test_async_decorator())
    
    print("\n=== Done ===\n")