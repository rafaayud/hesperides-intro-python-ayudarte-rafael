from src.trading.application.services.ingestion_service import DataIngestionService
from src.trading.domain.value_objects import Symbol, TimeFrame
from src.trading.infrastructure.binance_adapter import BinanceAdapter
from src.trading.infrastructure.postgre_adapter import PostgreAdapter
import logging
import asyncio
import aiohttp
import time

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

URL_DB = "postgresql://postgres:1234@localhost:5432/postgres"

async def test_ingest_and_sync(symbols: list[Symbol], intervals: list[TimeFrame]) -> None:
    """Test the ingestion and sync service"""
    try:
        async with DataIngestionService(storage=PostgreAdapter(URL_DB), exchange=BinanceAdapter()) as ingestion_service:
            await ingestion_service.sync_all(symbols, intervals)
    except Exception as e:
        logger.error(f"Error ingesting and syncing data: {e}")
        raise

async def get_all_binance_symbols() -> list[Symbol]:
    """Obtiene todos los pares USDT activos de Binance."""
    url = "https://api.binance.com/api/v3/exchangeInfo"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

           
            all_symbols = []
            for symbol in data["symbols"]:
                if symbol["symbol"].endswith("USDT") and symbol["status"] == "TRADING":
                    all_symbols.append(Symbol(symbol["symbol"]))

            return all_symbols



if __name__ == "__main__":
    # Symbols from project requirements: BTC, ETH, XRP, BNB, SOL, TRX, DOGE, ADA, LINK, HYPE
    symbols = [
        Symbol("BTCUSDT"),
        Symbol("ETHUSDT"),
        Symbol("BNBUSDT"),
        Symbol("SOLUSDT"),
        Symbol("XRPUSDT"),
        Symbol("ADAUSDT"),
        Symbol("DOGEUSDT"),
        Symbol("TRXUSDT"),
        Symbol("LINKUSDT"),
        #Symbol("HYPEUSDT"),
    ]
    m1 = TimeFrame.M1
    m5 = TimeFrame.M5
    m15 = TimeFrame.M15
    h1 = TimeFrame.H1
    h4 = TimeFrame.H4
    d1 = TimeFrame.D1
    w1 = TimeFrame.W1
    mo1 = TimeFrame.MO1

    intervals = [m1, m5, m15, h1, h4, d1, w1, mo1]
    all_symbols = asyncio.run(get_all_binance_symbols())

    test_symbols = all_symbols[:150]
    start_time = time.perf_counter()
    asyncio.run(test_ingest_and_sync(test_symbols, intervals))
    end_time = time.perf_counter()
    print(f"Time taken: {end_time - start_time} seconds")
   
   
