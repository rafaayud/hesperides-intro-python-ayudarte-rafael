"""
Trading Engine - Application Service for real-time trading.

Pipeline with 3 queues:
1. Candle Queue: WebSocket → Signal Processor
2. Order Queue: Signal Processor → Order Executor
3. Response Queue: Order Executor → Portfolio Updater
"""
import asyncio
import logging
from asyncio import Queue, TaskGroup

from typing import Dict, List, Set, Tuple
from decimal import Decimal
from datetime import datetime

from ...domain.ports import OrderPort, StreamPort, ExchangePort, PortfolioStoragePort
from ...domain.value_objects import Symbol, Interval, Signal, Quantity, Side, TradeStatus, Timestamp, Price
from ...domain.aggregates import Portfolio, Trader
from ...domain.entities import Candle, Position, Order, OrderResponse
from ...domain.utils.decorators import timed, timed_async

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Orchestrates real-time trading with a 3-queue pipeline.
    
    Queue 1: Candles (WebSocket → Traders)
    Queue 2: Order Requests (Traders → Binance)
    Queue 3: Order Responses (Binance → Portfolio)
    """
    
    def __init__(
        self,
        exchange: ExchangePort,
        stream: StreamPort,
        order: OrderPort,
        portfolio: Portfolio,
        portfolio_storage: PortfolioStoragePort) -> None:

        self._exchange = exchange
        self._stream = stream
        self._order = order
        self._portfolio = portfolio
        self._portfolio_storage = portfolio_storage
        
        # Index traders by (symbol, interval) for O(1) lookup when candle arrives
        self._traders = self._portfolio.traders
        self._traders_by_pair: Dict[Tuple[Symbol, Interval], List[Trader]] = {}

        # Index traders by (symbol, interval) so we do not ask to open more streams than necessary
        for trader in self._traders:
            key = (trader.symbol, trader.interval)
            if key not in self._traders_by_pair:
                self._traders_by_pair[key] = []
            self._traders_by_pair[key].append(trader)
        
        # 3 Queues
        self._candle_queue: Queue[Candle] = Queue(maxsize=1000)
        self._order_queue: Queue[Order] = Queue(maxsize=100)
        self._response_queue: Queue[Tuple[Order, OrderResponse]] = Queue(maxsize=100)
        
        self._running = False

    async def startup(self) -> None:
        """Warm-up all traders with historical data. Repasar porque creo que se puede hacer asincrono!!!!!!!!!"""
        logger.info(f"Warming up {len(self._traders)} traders...")
        
        for trader in self._traders:
            candles = await self._exchange.get_historical_candles(
                trader.symbol,
                trader.interval,
                limit=trader.strategy.min_candles_required + 10
            )
            trader.warm_up(candles)
            logger.info(f"Warmed up {trader.id}: {len(candles)} candles")
        
        logger.info("All traders ready!")

    async def run(self) -> None:
        """Run the trading pipeline."""
        self._running = True
        
        try:
            async with TaskGroup() as tg:
                # Stream tasks (WebSocket → Queue 1) - one per unique (symbol, interval)
                for (symbol, interval) in self._traders_by_pair.keys():
                    tg.create_task(self._stream_task(symbol, interval))
                
                # Signal processor (Queue 1 → Queue 2)
                tg.create_task(self._signal_processor())
                
                # Order executor (Queue 2 → Queue 3)
                tg.create_task(self._order_executor())
                
                # Portfolio updater (Queue 3 → Portfolio)
                tg.create_task(self._portfolio_updater())
                
        except* Exception as e:
            logger.error(f"Trading engine error: {e}")
            raise

    # ==================== TASK 1: Stream (WebSocket → Queue 1) ====================
    
    @timed_async
    async def _stream_task(self, symbol: Symbol, interval: Interval) -> None:
        """Receive candles from WebSocket and put in queue."""
        logger.info(f"Starting stream: {symbol}/{interval}")
        
        async for candle in self._stream.stream_candle(symbol, interval):
            if not self._running:
                break
            await self._candle_queue.put(candle)

    # ==================== TASK 2: Signal Processor (Queue 1 → Queue 2) ====================
    @timed_async
    async def _signal_processor(self) -> None:
        """Process candles, generate signals, create order requests."""
        logger.info("Signal processor started")
        
        while self._running:
            candle = await self._candle_queue.get()
            
            # O(1) lookup for matching traders
            key = (candle.symbol, candle.interval)
            traders = self._traders_by_pair.get(key, [])
            
            for trader in traders:
                signal = trader.on_candle(candle)
                
                if signal == Signal.HOLD:
                    continue
                
                # Create order
                order = await self._create_order(trader, signal, candle)
                if order:
                    await self._order_queue.put(order)
                    logger.info(f"Order queued: {trader.id} {signal.value} {candle.symbol}")
   
    @timed_async
    async def _create_order(self, trader: Trader, signal: Signal, candle: Candle) -> Order | None:
        """Create an order based on signal."""
        
        if signal == Signal.BUY:
            if self._portfolio.has_position(trader.id):
                logger.debug(f"{trader.id} already has position")
                return None
            
            # Calculate quantity using all capital
            capital = self._portfolio.get_capital(trader.id)
            price = await self._order.get_current_price(candle.symbol)
            quantity = Quantity(
                (capital / price.value).quantize(Decimal("0.00001"))
            )
            
            return Order(
                trader_id=trader.id,
                symbol=candle.symbol,
                side=Side.BUY,
                quantity=quantity,
                price=price
            )
        
        elif signal == Signal.SELL:
            if not self._portfolio.has_position(trader.id):
                logger.debug(f"{trader.id} has no position")
                return None
            
            position = self._portfolio.get_position(trader.id)
            price = await self._order.get_current_price(candle.symbol)
            
            return Order(
                trader_id=trader.id,
                symbol=candle.symbol,
                side=Side.SELL,
                quantity=position.quantity,
                price=price
            )
        
        return None

    # ==================== TASK 3: Order Executor (Queue 2 → Queue 3) ====================
    
    @timed_async
    async def _order_executor(self) -> None:
        """Execute orders on Binance and put responses in queue."""
        logger.info("Order executor started")
        
        while self._running:
            order = await self._order_queue.get()
            
            try:
                if order.side == Side.BUY:
                    response = await self._order.buy_market(order.symbol, order.quantity)
                else:
                    response = await self._order.sell_market(order.symbol, order.quantity)
                
                await self._response_queue.put((order, response))
                logger.info(f"Order executed: {order.trader_id} {order.side.value} → {response.status.value}")
                
            except Exception as e:
                logger.error(f"Order failed for {order.trader_id}: {e}")

    # ==================== TASK 4: Portfolio Updater (Queue 3 → Portfolio) ====================
    
    @timed_async
    async def _portfolio_updater(self) -> None:
        """Update portfolio based on order responses."""
        logger.info("Portfolio updater started")
        
        while self._running:
            order, response = await self._response_queue.get()
            
            if response.status != TradeStatus.EXECUTED:
                logger.warning(f"Order not executed: {order.trader_id} → {response.status.value}")
                continue
            
            if order.side == Side.BUY:
                position = Position(
                    symbol=order.symbol,
                    side=Side.BUY,
                    entry_price=response.price,
                    quantity=response.quantity,
                    entry_time=Timestamp(datetime.now()),
                    target_quantity=response.quantity,
                    status=TradeStatus.EXECUTED
                )
                self._portfolio.open_position(order.trader_id, position)
                logger.info(f"Position opened: {order.trader_id} @ {response.price}")
                
            elif order.side == Side.SELL:

                self._portfolio.close_position(order.trader_id, response)
                logger.info(f"Position closed: {order.trader_id} @ {response.price}")

    # ==================== Helpers ====================
    
    def _get_unique_pairs(self) -> Set[Tuple[Symbol, Interval]]:
        """Get unique symbol/interval pairs."""
        return set(self._traders_by_pair.keys())

    async def stop(self) -> None:
        """Stop the trading engine."""
        self._running = False
        logger.info("Trading engine stopped")

    async def __aenter__(self) -> "TradingEngine":
        await self._exchange.connect()
        await self._stream.connect()
        await self._order.connect()
        await self._portfolio_storage.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
        await self._stream.disconnect()
        await self._order.disconnect()
        await self._exchange.disconnect()
        await self._portfolio_storage.disconnect()
