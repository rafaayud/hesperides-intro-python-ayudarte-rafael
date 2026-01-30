"""
Test del Trading Engine en vivo (sin API).
Testea directamente el motor de trading desde una capa más abajo.

USO:
    python tests/test_trading_engine_live.py --portfolio-id <ID>
    
O sin argumentos para crear un portfolio de prueba.
"""
import sys
import os

# Add server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
import argparse
from decimal import Decimal
from datetime import datetime

from modules.trading.application.services.trading_engine import TradingEngine
from modules.trading.application.services.portfolio_manager import PortfolioManager
from modules.trading.domain.aggregates import Portfolio, Trader
from modules.trading.domain.value_objects import Interval, Symbol, ExecutionMode
from modules.trading.domain.strategies.mock_strategy import MockStrategy
from modules.trading.domain.strategies.mean_cross import MeanCross
from modules.trading.domain.strategies.momentum import Momentum

from apps.api.config import get_settings
from apps.api.registry import AdapterRegistry
from apps.api.dependencies import setup_registry
from apps.api.service_factory import ServiceFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set specific loggers
logging.getLogger('modules.trading.application.services.trading_engine').setLevel(logging.INFO)
logging.getLogger('modules.trading.application.services.portfolio_manager').setLevel(logging.INFO)
logging.getLogger('modules.trading.domain.aggregates.trader').setLevel(logging.INFO)

# Reduce noise
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def create_test_portfolio(portfolio_manager: PortfolioManager, portfolio_id: str = "test_live_1") -> Portfolio:
    """Create a test portfolio for live testing"""
    logger.info(f"Creating test portfolio: {portfolio_id}")
    
    # Create traders with different strategies
    traders = [
        Trader(
            id="trader_1",
            strategy=MeanCross(slow_period=50, fast_period=10, mode=ExecutionMode.ON_CLOSE),
            symbol=Symbol("BTCUSDT"),
            interval=Interval.M1  # 1 minuto para ver acción rápida
        ),
        Trader(
            id="trader_2",
            strategy=Momentum(reference_period=14, threshold=0.02),
            symbol=Symbol("ETHUSDT"),
            interval=Interval.M1
        ),
    ]
    
    portfolio = Portfolio(
        id=portfolio_id,
        name="Test Live Portfolio",
        initial_capital=Decimal("10000"),
        traders=traders
    )
    
    # Save portfolio
    portfolio_manager._portfolio = portfolio
    await portfolio_manager.save_portfolio()
    logger.info(f"✅ Portfolio {portfolio_id} created with {len(traders)} traders")
    
    return portfolio


async def load_portfolio(portfolio_manager: PortfolioManager, portfolio_id: str) -> Portfolio:
    """Load portfolio from database"""
    logger.info(f"Loading portfolio: {portfolio_id}")
    portfolio = await portfolio_manager.load_portfolio(portfolio_id)
    logger.info(f"✅ Portfolio loaded: {portfolio.name} with {len(portfolio.traders)} traders")
    return portfolio


async def monitor_portfolio(portfolio_manager: PortfolioManager, interval: int = 10):
    """Monitor portfolio state periodically"""
    while True:
        await asyncio.sleep(interval)
        
        if portfolio_manager._portfolio is None:
            continue
        
        portfolio = portfolio_manager._portfolio
        print("\n" + "=" * 80)
        print(f"PORTFOLIO STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)
        print(f"Portfolio: {portfolio.name} (ID: {portfolio.id})")
        print(f"Initial Capital: ${portfolio.initial_capital:,.2f}")
        print(f"Total PnL: ${portfolio.total_pnl:,.2f}")
        print(f"Total PnL %: {portfolio.total_pnl_percentage:.2f}%")
        print(f"Active Positions: {len(portfolio.get_open_positions())}")
        print(f"Total Trades: {sum(len(portfolio.get_trades_by_trader(t.id)) for t in portfolio.traders)}")
        
        # Show traders status
        print("\nTraders:")
        for trader in portfolio.traders:
            position = portfolio.get_position(trader.id)
            trades = portfolio.get_trades_by_trader(trader.id)
            trader_pnl = sum(t.pnl.value for t in trades)
            
            position_str = "None"
            if position:
                position_str = f"{position.side.value} {position.quantity.value} @ ${position.entry_price.value:,.2f}"
            
            print(f"  • {trader.id}: {trader.symbol.symbol} {trader.interval.value}")
            print(f"    Position: {position_str}")
            print(f"    Trades: {len(trades)} | PnL: ${trader_pnl:,.2f}")
        
        print("=" * 80 + "\n")


async def run_trading_engine(portfolio_id: str, duration_minutes: int = 5):
    """Run trading engine for a specified duration"""
    
    print("=" * 80)
    print("TRADING ENGINE - LIVE TEST")
    print("=" * 80)
    print(f"Portfolio ID: {portfolio_id}")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("\nPress Ctrl+C to stop\n")
    
    # Initialize
    settings = get_settings()
    setup_registry(settings)
    registry = AdapterRegistry()
    service_factory = ServiceFactory(registry, settings)
    
    # Create portfolio manager
    portfolio_manager = service_factory.create_portfolio_manager()
    await portfolio_manager.connect()
    
    try:
        # Try to load portfolio, if not exists, create it
        try:
            portfolio = await load_portfolio(portfolio_manager, portfolio_id)
        except ValueError:
            logger.warning(f"Portfolio {portfolio_id} not found, creating test portfolio...")
            portfolio = await create_test_portfolio(portfolio_manager, portfolio_id)
        
        # Create trading engine
        engine = service_factory.create_trading_engine(
            exchange=None,  # Use defaults (Binance)
            stream=None,    # Use defaults (Binance Stream)
            order=None,     # Use defaults (Binance Order)
            portfolio_manager=portfolio_manager
        )
        
        # Connect adapters
        await engine._exchange.connect()
        await engine._stream.connect()
        await engine._order.connect()
        
        # Startup engine (restore state and warm-up)
        logger.info("Starting up trading engine...")
        await engine.startup()
        logger.info("✅ Trading engine started!")
        
        # Start monitoring task
        monitor_task = asyncio.create_task(monitor_portfolio(portfolio_manager, interval=10))
        
        try:
            # Run engine for specified duration
            if duration_minutes > 0:
                logger.info(f"Running for {duration_minutes} minutes...")
                await asyncio.wait_for(engine.run(), timeout=duration_minutes * 60)
            else:
                # Run indefinitely
                logger.info("Running indefinitely (press Ctrl+C to stop)...")
                await engine.run()
                
        except asyncio.TimeoutError:
            logger.info(f"⏰ {duration_minutes} minutes elapsed, stopping...")
        except KeyboardInterrupt:
            logger.info("\n⚠️  Interrupted by user (Ctrl+C)")
        finally:
            # Stop monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
            
            # Stop engine
            logger.info("Stopping trading engine...")
            await engine.stop()
            
            # Final save
            await portfolio_manager.periodic_save()
            
            # Disconnect
            await engine._stream.disconnect()
            await engine._order.disconnect()
            await engine._exchange.disconnect()
            
            # Final status
            print("\n" + "=" * 80)
            print("FINAL STATUS")
            print("=" * 80)
            portfolio = portfolio_manager._portfolio
            if portfolio:
                print(f"Portfolio: {portfolio.name}")
                print(f"Total PnL: ${portfolio.total_pnl:,.2f} ({portfolio.total_pnl_percentage:.2f}%)")
                print(f"Total Trades: {sum(len(portfolio.get_trades_by_trader(t.id)) for t in portfolio.traders)}")
                print(f"Active Positions: {len(portfolio.get_open_positions())}")
            print("=" * 80)
            
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise
    finally:
        await portfolio_manager.disconnect()
        logger.info("✅ All connections closed")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test Trading Engine live (without API)")
    parser.add_argument(
        "--portfolio-id",
        type=str,
        default="test_live_1",
        help="Portfolio ID to use (default: test_live_1, will create if doesn't exist)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Duration in minutes (default: 5, use 0 for infinite)"
    )
    
    args = parser.parse_args()
    
    try:
        await run_trading_engine(args.portfolio_id, args.duration)
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
