import asyncio
from trading.infrastructure.binance_adapter import BinanceAdapter
from trading.domain.value_objects import Symbol, TimeFrame

async def main():
    

    async with BinanceAdapter() as adapter:
        candles = await adapter.get_historical_candles(
            symbol="BTCUSDT",
            interval=TimeFrame.H1,
            limit=100
        )
        for candle in candles:
            print(f"Timestamp: {candle.timestamp.timestamp} | Open: {candle.open} | High: {candle.high} | Low: {candle.low} | Close: {candle.close} | Volume: {candle.volume}")

if __name__ == "__main__":
    asyncio.run(main())