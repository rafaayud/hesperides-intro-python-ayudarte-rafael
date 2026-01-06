import asyncio
import logging
from src.trading.application.services.ingestion_service import DataIngestionService
from src.trading.infrastructure import BinanceAdapter, PostgreAdapter
from src.trading.domain.value_objects import TimeFrame, Symbol
from time import perf_counter

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

URL_DB = "postgresql://postgres:1234@localhost:5432/postgres"


async def test_ingestion_service() -> None:
    """Test the ingestion service and verify data is saved"""
    print("🚀 Starting ingestion test...")
    
    exchange = BinanceAdapter()
    storage = PostgreAdapter(URL_DB)
    
    # Use context manager - automatically handles startup/shutdown
    start_time = perf_counter()
    async with DataIngestionService(storage, exchange) as service:
        symbol = Symbol("BTCUSDT")
        interval = TimeFrame.M1
        
        # Run ingestion
        print("📥 Running ingestion...")
        await service.run(symbol, interval)

        #last_candle = await storage.get_last_candle(symbol, interval)
        #print(f"Last candle: {last_candle}")
        
    end_time = perf_counter()
    print(f"Time taken: {end_time - start_time} seconds")
    print("✅ Test completed (context manager automatically closed connections)")


if __name__ == "__main__":  # Fixed: was __main__
    asyncio.run(test_ingestion_service())