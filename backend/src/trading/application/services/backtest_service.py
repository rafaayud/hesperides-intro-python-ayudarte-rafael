from trading.domain.value_objects import Symbol, Interval, Candle_static, Signal, Side, Quantity, TradeStatus
from trading.domain.entities import Candle, Position, Trade, BacktestResult
from trading.domain.strategies.base import Strategy
from trading.domain.ports import StoragePort
import asyncio
from datetime import datetime
import logging
from decimal import Decimal


class BacktestService:
    """Service for backtesting strategies, we take all the candles for a given symbol and timeframe and test the strategy."""

    def __init__(self, storage: StoragePort) -> None:
        self._storage = storage
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.INFO)  # Changed to DEBUG to see debug logs

    async def connect(self) -> None:
        await self._storage.connect()
        self._logger.info("Connected to storage")

    async def disconnect(self) -> None:
        await self._storage.disconnect()
        self._logger.info("Disconnected from storage")

    async def get_candles(self, symbol: Symbol, interval: Interval) -> list[Candle_static]:
        """Get all the candles for a given symbol and timeframe"""

        if not self._storage:
            raise ValueError("Storage not connected")

        limit = interval.max_candles

        candles = await self._storage.get_candles(symbol, interval, limit)
        return candles

    def test_strategy(self, strategy: Strategy, candles: list[Candle_static], initial_capital: float) -> None:
        """Test a strategy with a list of candles"""

        candles = [Candle.from_static(c) for c in candles]

        window = []
        position = None
        trades = []
        capital = Decimal(initial_capital)

        for candle in candles:
            window.append(candle)

            if len(window) < strategy.min_candles_required:
                continue

            signal = strategy.generate_signal(window)
            self._logger.debug(f"Signal: {signal} at candle {len(window)}")


            #We start our position buying
            if signal == Signal.BUY and position is None:
                quantity = capital / candle.close.value
                position = Position(
                    symbol=candle.symbol,
                    side=Side.BUY,
                    entry_price=candle.close,
                    quantity=Quantity(quantity),
                    entry_time=candle.event_time,
                    target_quantity=Quantity(quantity),
                    status=TradeStatus.EXECUTED,
                )
                self._logger.info(f" BUY Position opened: {position.symbol} @ ${position.entry_price.value:.2f}, qty: {position.quantity.value:.4f}")
    
            #We close our position selling
            elif signal == Signal.SELL and position is not None:
                trade = position.close(candle.close, candle.event_time)
                trades.append(trade)
                capital += trade.pnl.value
                pnl_str = f"+${trade.pnl.value:.2f}" if trade.pnl.value >= 0 else f"${trade.pnl.value:.2f}"
                self._logger.info(f" SELL Position closed: {trade.symbol} @ ${trade.exit_price.value:.2f}, PnL: {pnl_str}, Capital: ${capital:.2f}")
                position = None
        #We close our position at the end of the backtest
        if position is not None:
            last_candle = candles[-1]  # candles is already a list of Candle, not Candle_static
            trade = position.close(last_candle.close, last_candle.event_time)
            trades.append(trade)
            capital += trade.pnl.value
            pnl_str = f"+${trade.pnl.value:.2f}" if trade.pnl.value >= 0 else f"${trade.pnl.value:.2f}"
            
        
        self._logger.info(f" Backtest completed: {len(trades)} trades, Final capital: ${float(capital):.2f}")
            
        return BacktestResult(
            symbol=candles[0].symbol,
            interval=candles[0].interval,
            strategy_name=strategy.name,
            initial_capital=initial_capital,
            final_capital=float(capital),
            trades=tuple(trades)
        )



    async def __aenter__(self) -> "BacktestService":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.disconnect()