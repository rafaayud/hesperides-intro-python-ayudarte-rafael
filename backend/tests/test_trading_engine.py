from src.trading.application.services.trading_engine import TradingEngine
from src.trading.domain.value_objects import Symbol, Interval, ExecutionMode, Candle_static, Signal
from src.trading.domain.strategies.mean_cross import MeanCross
from src.trading.domain.strategies.mock_strategy import MockStrategy
from src.trading.domain.aggregates import Trader, CandleBuffer, Portfolio
from src.trading.infrastructure.mocks.mock_exchange_adapter import MockExchangeAdapter
from src.trading.infrastructure.mocks.mock_stream_adapter import MockStreamAdapter
from src.trading.infrastructure.mocks.mock_order_adapter import MockOrderAdapter
from src.trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter
from src.trading.infrastructure.binance_adapter import BinanceAdapter
from src.trading.infrastructure.binance_order_adapter import BinanceOrderAdapter

import asyncio
from decimal import Decimal
import logging
import sys
from asyncio import Queue
from src.trading.domain.entities import Candle

CANDLES = 20
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] # Fuerza la salida estándar
)
logger = logging.getLogger(__name__)

mock_exchange = MockExchangeAdapter()
mock_stream = MockStreamAdapter()
binance_stream = BinanceStreamAdapter()
mock_order = MockOrderAdapter()
trader_1 = Trader(id="1", strategy=MeanCross(fast_period=10, slow_period=40, mode=ExecutionMode.ON_CLOSE), symbol=Symbol("BTCUSDT"), interval=Interval.M1)
trader_2 = Trader(id="2", strategy=MeanCross(fast_period=10, slow_period=40, mode=ExecutionMode.ON_CLOSE), symbol=Symbol("BTCUSDT"), interval=Interval.M5)
trader_3 = Trader(id="3", strategy=MockStrategy(name="MockStrategy", min_candles=1, mode=ExecutionMode.ON_CLOSE), symbol=Symbol("BTCUSDT"), interval=Interval.M1)
async def prueba_trader_warmup() -> None:

    portfolio = Portfolio(initial_capital=Decimal("100000"), traders=[trader_1])
    logger.info(f"Portfolio created with capital: {portfolio.initial_capital} and {len(portfolio.traders)} traders, traders follow the strategy: {trader_1.strategy.name}")

    trading_engine = TradingEngine(exchange=mock_exchange, stream=mock_stream, order=mock_order, portfolio=portfolio)

    await trading_engine.startup()
    logger.info("Traders loaded with candles")


async def prueba_trader_stream_feed() -> None:
    """Test that candles are streamed and added to queue, then processed by trader."""
    candle_queue = Queue(maxsize=1000)

    portfolio = Portfolio(initial_capital=Decimal("100000"), traders=[trader_1])
    logger.info(f"Portfolio created with capital: {portfolio.initial_capital} and {len(portfolio.traders)} traders, traders follow the strategy: {trader_1.strategy.name}")

    trading_engine = TradingEngine(exchange=mock_exchange, stream=mock_stream, order=mock_order, portfolio=portfolio)

    await trading_engine.startup()
    logger.info("Traders warmed up, starting stream test...")

    # Producer task: stream candles and add to queue
    async def producer() -> None:
        logger.info("Producer started: streaming candles...")
        count = 0
        # Use context manager to connect/disconnect automatically
        async with binance_stream:
            logger.info("Connected to Binance stream")
            # Stream candles (stream_candle is an async generator)
            async for candle in binance_stream.stream_candle(Symbol("BTCUSDT"), Interval.M1):
                logger.info(f"Streaming candle #{count}: {candle.open_time.timestamp}, symbol: {candle.symbol}, interval: {candle.interval.value}, is_closed: {candle.is_closed}")
                await candle_queue.put(candle)
                count += 1
                if count >= CANDLES:  # Stop after 10 candles for testing
                    logger.info("Producer finished: 10 candles streamed")

                    break
        logger.info("Disconnected from Binance stream")

    # Consumer task: get candles from queue and process with trader
    async def consumer() -> None:
        logger.info("Consumer started: waiting for candles...")
        count = 0
        while True:
            candle = await candle_queue.get()
            count += 1
            logger.info(f"Consumer got candle #{count} from queue (queue size: {candle_queue.qsize()})")
            logger.info(f"Candle: {candle.open_time.timestamp} - {candle.symbol} {candle.interval.value}")
            
            signal = trader_1.on_candle(candle)
            logger.info(f"Trader signal: {signal.value}")
            
            if count >= CANDLES:  # Stop after processing 10 candles
                logger.info(f"Consumer finished: {CANDLES} candles processed")
                logger.info(f"trader_1_candles: {Candle_static._print_table(trader_1.get_closed_candles())}")
                break
        
        print(f"trader_1_candles: {Candle_static._print_table(trader_1.get_closed_candles())}")


    # Run producer and consumer concurrently
    await asyncio.gather(producer(), consumer())
    logger.info("Test completed!")


async def test_order_creation_queu_execution(self) -> None:
    """Test that orders are created and executed."""
    portfolio = Portfolio(initial_capital=Decimal("100000"), traders=[trader_1])
    ordenes = []
    cola = Queue(maxsize=1000)


async def test_trading_engine() -> None:
    """Test the trading engine."""
    try:
        portfolio = Portfolio(initial_capital=Decimal("100000"), traders=[trader_3, trader_1])
        trading_engine = TradingEngine(exchange=mock_exchange, stream=mock_stream, order=mock_order, portfolio=portfolio)
        await trading_engine.startup()
        logger.info("Traders loaded with candles")
        
        # Ejecutar el engine por 30 segundos y luego TimeoutError
        try:
            await asyncio.wait_for(trading_engine.run(), timeout=30)
        except asyncio.TimeoutError:
            logger.info("Trading engine stopped after 30 seconds")
        
    except Exception as e:
        logger.error(f"Error in trading engine: {e}")
        raise e
    
    finally:
        await trading_engine.stop()
        logger.info("Trading engine stopped")

        print(f"portfolio: {portfolio}")



async def test_trading_with_adapters() -> None:
    """Test the trading engine with adapters."""
    binance_adapter = BinanceAdapter()
    binance_order_adapter = BinanceOrderAdapter()
    binance_stream_adapter = BinanceStreamAdapter()
    mock_stream = MockStreamAdapter()
    portfolio = Portfolio(initial_capital=Decimal("100000"), traders=[trader_3, trader_1])
    trading_engine = TradingEngine(exchange=binance_adapter, stream=binance_stream_adapter, order=binance_order_adapter, portfolio=portfolio)
    
    async with trading_engine as engine:
        await engine.startup()
        logger.info("Traders loaded with candles")
        await engine.run()
        logger.info("Trading engine running")
        await asyncio.sleep(30)
        await engine.stop()
        logger.info("Trading engine stopped")
        print(f"portfolio: {portfolio}")


if __name__ == "__main__":


    asyncio.run(test_trading_with_adapters())
    







