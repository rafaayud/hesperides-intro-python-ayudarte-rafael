from modules.trading.application.services.trading_engine import TradingEngine
from modules.trading.infrastructure.postgres_portfolio_adapter import PostgresPortfolioAdapter
from modules.trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter
from modules.trading.infrastructure.binance_order_adapter import BinanceOrderAdapter
from modules.trading.infrastructure.binance_adapter import BinanceAdapter

from modules.trading.infrastructure.mocks.mock_order_adapter import MockOrderAdapter
from modules.trading.infrastructure.mocks.mock_stream_adapter import MockStreamAdapter

from modules.trading.domain.aggregates import Portfolio, Trader
from modules.trading.domain.value_objects import Interval, Symbol
from modules.trading.domain.strategies.mock_strategy import MockStrategy

from apps.api.config import get_settings

import asyncio
import logging

from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Función principal del script."""
    # Obtener configuración de la base de datos
    settings = get_settings()
    
    trader = Trader(
        id="test_trader_1", 
        strategy=MockStrategy(name="TestStrategy", min_candles=10), 
        symbol=Symbol("BTCUSDT"), 
        interval=Interval.M1
    )
    
    portfolio = Portfolio(
        id="test_portfolio_2", 
        name="Test Portfolio2", 
        initial_capital=Decimal("1000"), 
        traders=[trader]
    )
    
    exchange = BinanceAdapter()
    stream = BinanceStreamAdapter()
    stream_mock = MockStreamAdapter()
    order_mock = MockOrderAdapter()
    db_adapter = PostgresPortfolioAdapter(db_url=settings.database_url)
    
    engine = TradingEngine(
        exchange=exchange, 
        stream=stream_mock, 
        order=order_mock, 
        portfolio=portfolio, 
        portfolio_storage=db_adapter
    )
    
    try:
        

        async with engine as engine:
            await engine.startup()
            print("✅ Trading engine started! Press Ctrl+C to stop.\n")
            
            # Monitor del portfolio en background
            async def monitor_portfolio():
                while True:
                    await asyncio.sleep(10)  # Cada 10 segundos
                    print("\n" + str(portfolio) + "\n")
            
            monitor_task = asyncio.create_task(monitor_portfolio())
            
            try:
                await engine.run()
            finally:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            
    except KeyboardInterrupt:
        print("\n⚠️  Stopping trading engine...")
    finally:
        await engine.stop()
        await exchange.disconnect()
        await stream.disconnect()
        await db_adapter.disconnect()
        pnl = engine._portfolio.total_pnl
        print("✅ All connections closed.")
        

if __name__ == "__main__":
    asyncio.run(main())







