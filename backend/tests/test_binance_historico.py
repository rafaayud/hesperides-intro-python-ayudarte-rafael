import asyncio
import logging
from datetime import datetime
from src.trading.infrastructure.binance_adapter import BinanceAdapter
from src.trading.domain.value_objects import Symbol, Interval

logging.basicConfig(level=logging.INFO)


async def main():
    async with BinanceAdapter() as adapter:
        print("\n=== Testing get_historical_candles ===\n")
        
        candles = await adapter.get_historical_candles(
            symbol=Symbol("BTCUSDT"),
            interval=Interval.H1,
            limit=10
        )
        
        print(f"Requested: 10 candles")
        print(f"Received: {len(candles)} candles\n")
        
        # Show last 5 candles
        print("Last 5 candles:")
        for candle in candles[-5:]:
            print(candle)
        
        # Verify the most recent candle is closed (not current hour)
        if candles:
            last_candle = candles[-1]
            now = datetime.now()
            candle_hour = last_candle.timestamp.timestamp.hour
            current_hour = now.hour
            
            print(f"\nLast candle hour: {candle_hour}")
            print(f"Current hour: {current_hour}")
            
            if candle_hour != current_hour:
                print("✓ Last candle is CLOSED (different hour)")
            else:
                print("⚠ Last candle might still be OPEN (same hour)")


if __name__ == "__main__":
    asyncio.run(main())