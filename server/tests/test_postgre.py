import asyncio
from decimal import Decimal
from datetime import datetime, timezone

from modules.trading.domain.value_objects import Symbol, Price, Quantity, Timestamp, TimeFrame, Candle_static
from modules.trading.infrastructure import PostgresAdapter, BinanceAdapter

URL_DB = "postgresql://trading:trading123@localhost:5432/trading_db"
async def test_save_candle() -> None:
    """Test the save_candle method"""
    async with PostgresAdapter(URL_DB) as db:
        candle = Candle_static(
            symbol=Symbol("BTCUSDT"),
            interval=TimeFrame.M1,
            timestamp=Timestamp(datetime.now(timezone.utc)),
            open=Price(Decimal("95000")),
            high=Price(Decimal("95500")),
            low=Price(Decimal("94800")),
            close=Price(Decimal("95200")),
            volume=Quantity(Decimal("125.5"))
        )
        
        await db.save_candle(candle)
        print("Candle guardada!")
        #await db.delete_candles(Symbol("BTCUSDT"), TimeFrame.M1)

async def test_get_candles() -> None:
    """Test the get_candles method"""
    async with PostgresAdapter(URL_DB) as db:
        candles = await db.get_candles(Symbol("BTCUSDT"), TimeFrame.M1, 100)
        Candle_static._print_table(candles)


async def test_delete_candles() -> None:
    """Test the delete_candles method"""
    async with PostgresAdapter(URL_DB) as db:
        await db.delete_candles(Symbol("BTCUSDT"), TimeFrame.M1)
        print("Candles deleted!")


async def test_ingest_storage() -> None:
    """Test the ingest_storage method"""
    async with BinanceAdapter() as binance:
        candles = await binance.get_historical_candles(Symbol("BTCUSDT"), TimeFrame.M1, 100)
        async with PostgresAdapter(URL_DB) as db:
            for candle in candles:
                await db.save_candle(candle)
            print("Candles ingested!")


if __name__ == "__main__":
    asyncio.run(test_ingest_storage())
    asyncio.run(test_get_candles())

