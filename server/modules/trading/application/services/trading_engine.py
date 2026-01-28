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

from ...domain.ports import OrderPort, StreamPort, ExchangePort
from ...application.services.portfolio_manager import PortfolioManager
from ...domain.value_objects import Symbol, Interval, Signal, Quantity, Side, TradeStatus, Timestamp, Price

from ...domain.aggregates import Trader
from ...domain.entities import Candle, Position, Order, OrderResponse, Trade
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
        portfolio_manager: PortfolioManager | None = None) -> None:

        self._exchange = exchange
        self._stream = stream
        self._order = order
        self._portfolio_manager = portfolio_manager
        
        # Index traders by (symbol, interval) for O(1) lookup when candle arrives
        self._traders_by_pair: Dict[Tuple[Symbol, Interval], List[Trader]] = {}
        
        # Initialize traders if portfolio manager is provided
        if portfolio_manager is not None:
            self._index_traders()
        
        # 3 Queues
        self._candle_queue: Queue[Candle] = Queue(maxsize=1000)
        self._order_queue: Queue[Order] = Queue(maxsize=100)
        self._response_queue: Queue[Tuple[Order, OrderResponse]] = Queue(maxsize=100)
        
        self._running = False

    def initialize_portfolio_manager(self, portfolio_manager: PortfolioManager) -> None:
        """Initialize portfolio manager and index traders."""
        self._portfolio_manager = portfolio_manager
        self._index_traders()
    
    def _index_traders(self) -> None:
        """Index traders by (symbol, interval) for efficient lookup."""
        if self._portfolio_manager is None:
            return
        
        traders = self._portfolio_manager.traders
        self._traders_by_pair = {}
        for trader in traders:
            key = (trader.symbol, trader.interval)
            if key not in self._traders_by_pair:
                self._traders_by_pair[key] = []
            self._traders_by_pair[key].append(trader)



    async def _warm_up_traders(self) -> None:
        """Warm-up all traders with historical data."""
        if self._portfolio_manager is None:
            return
        
        traders = self._portfolio_manager.traders
        logger.info(f"Warming up {len(traders)} traders...")
        
        for trader in traders:
            candles = await self._exchange.get_historical_candles(
                trader.symbol,
                trader.interval,
                limit=trader.strategy.min_candles_required + 10
            )
            trader.warm_up(candles)
            logger.info(f"Warmed up {trader.id}: {len(candles)} candles")
        
        logger.info("All traders ready!")

    async def startup(self) -> None:
        """Initialize trading engine: restore portfolio state and warm-up traders."""
        if self._portfolio_manager is None:
            raise ValueError("Portfolio manager must be initialized before calling startup()")
        
        # Step 1: Restore portfolio state from database (or create new)
        await self._portfolio_manager.restore_state()
        
        # Step 2: Warm-up traders with historical data
        await self._warm_up_traders()

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
            logger.info(f"Candle received: {candle.symbol}/{candle.interval} @ {candle.close.value}")
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
                logger.info(f"Candle received for {trader.id}: signal={signal.value}")
                
                if signal == Signal.HOLD:
                    continue
                
                # Create order
                order = await self._create_order(trader, signal, candle)
                if order:
                    await self._order_queue.put(order)
                    logger.info(f"Order queued: {trader.id} {signal.value} {candle.symbol}")
                else:
                    logger.info(f"Order not created for {trader.id} {signal.value}")
   
    @timed_async
    async def _create_order(self, trader: Trader, signal: Signal, candle: Candle) -> Order | None:
        """Create an order based on signal."""
        
        if self._portfolio_manager is None:
            return None
        
        if signal == Signal.BUY:
            if self._portfolio_manager.has_position(trader.id):
                logger.info(f"{trader.id} already has position")
                return None
            
            # Calculate quantity using all capital
            capital = self._portfolio_manager.get_capital(trader.id)
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
            if not self._portfolio_manager.has_position(trader.id):
                logger.info(f"{trader.id} has no position")
                return None
            
            position = self._portfolio_manager.get_position(trader.id)
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
        
        if self._portfolio_manager is None:
            logger.error("Portfolio manager not initialized")
            return
        
        while self._running:
            order, response = await self._response_queue.get()
            
            if response.status != TradeStatus.EXECUTED:
                logger.warning(f"Order not executed: {order.trader_id} → {response.status.value}")
                continue
            
            try:
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
                    await self._portfolio_manager.open_position(order.trader_id, position)
                    logger.info(f"🟢 BUY {order.trader_id} | {order.symbol.symbol} @ ${response.price.value:,.2f} | Qty: {response.quantity.value}")
                    
                elif order.side == Side.SELL:
                    trade = await self._portfolio_manager.close_position(order.trader_id, response)
                    status = "✅" if trade.winner else "❌"
                    logger.info(f"🔴 SELL {order.trader_id} | {trade.symbol.symbol} | Entry: ${trade.entry_price.value:,.2f} → Exit: ${trade.exit_price.value:,.2f} | PnL: ${trade.pnl.value:+,.2f} ({trade.pnl_percentage:+.2f}%) {status}")
                    
            except Exception as e:
                logger.error(f"Error updating portfolio for {order.trader_id}: {e}", exc_info=True)

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
        if self._portfolio_manager:
            await self._portfolio_manager.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
        await self._stream.disconnect()
        await self._order.disconnect()
        await self._exchange.disconnect()
        if self._portfolio_manager:
            await self._portfolio_manager.disconnect()
