"""Regression checks: exchange time -> domain -> API, without live orders."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from apps.api.controllers.candle_controller import CandleController
from modules.trading.application.services.trading_engine import TradingEngine
from modules.trading.domain.aggregates.candle_buffer import CandleBuffer
from modules.trading.domain.entities import Candle, Order, OrderResponse
from modules.trading.domain.value_objects import Interval, Price, Quantity, Side, Symbol, Timestamp, TradeStatus
from modules.trading.infrastructure.binance_adapter import BinanceAdapter
from modules.trading.infrastructure.binance_order_adapter import BinanceOrderAdapter
from modules.trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter
from modules.trading.infrastructure.postgre_adapter import PostgresAdapter


@pytest.mark.parametrize('date', ['2026-01-15T12:00:00', '2026-07-15T12:00:00', '2026-10-25T01:30:00'])
def test_exchange_rest_stream_order_and_api_agree_on_utc(date):
    instant = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    milliseconds = int(instant.timestamp() * 1000)
    symbol = Symbol('BTCUSDT')
    candle = BinanceAdapter()._parse_candle(symbol, [milliseconds, '100', '110', '90', '105', '2'], Interval.M1)
    live = BinanceStreamAdapter()._parse_kline({
        'E': milliseconds + 1234,
        'k': {'s': 'BTCUSDT', 'i': '1m', 't': milliseconds, 'T': milliseconds + 59999,
              'o': '100', 'h': '110', 'l': '90', 'c': '105', 'v': '2', 'n': 3, 'x': True},
    })
    # Parsing only: these placeholder credentials are never sent to an exchange.
    order = BinanceOrderAdapter(api_key='test-placeholder', api_secret='test-placeholder')._parse_response({
        'status': 'FILLED', 'orderId': 1, 'executedQty': '2', 'price': '105',
        'transactTime': milliseconds + 1234,
    }, symbol, Side.BUY)
    assert candle.timestamp.timestamp == instant
    assert live.open_time == candle.timestamp
    assert live.event_time == order.timestamp
    assert live.close_time.timestamp == instant + timedelta(milliseconds=59999)
    assert live.ingestion_time.timestamp.utcoffset() == timedelta(0)
    serialized = CandleController().serialize_candle(candle)
    assert serialized['open_time'] == instant.isoformat()
    assert datetime.fromisoformat(serialized['open_time']).timestamp() == milliseconds / 1000


def test_timestamp_normalizes_offsets_and_repeated_daylight_saving_hour():
    madrid = ZoneInfo('Europe/Madrid')
    first = Timestamp(datetime(2026, 10, 25, 2, 30, tzinfo=madrid, fold=0))
    second = Timestamp(datetime(2026, 10, 25, 2, 30, tzinfo=madrid, fold=1))
    assert second.timestamp - first.timestamp == timedelta(hours=1)
    assert first < second
    assert Timestamp(datetime(2026, 1, 1)).timestamp == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_candle_buffer_closes_aligned_utc_candles_and_ignores_duplicates():
    candle = BinanceAdapter()._parse_candle(Symbol('BTCUSDT'), [1767225600000, '100', '110', '90', '105', '2'], Interval.M1)
    live = Candle.from_static(candle)
    buffer = CandleBuffer(interval=Interval.M1, session_origin=candle.timestamp)
    buffer.on_candle_update(live)
    buffer.on_candle_close(live)
    buffer.on_candle_update(live)
    buffer.on_candle_close(live)
    assert len(buffer.closed_candles) == 1
    assert buffer.closed_candles[0].timestamp == candle.timestamp


@pytest.mark.asyncio
async def test_position_uses_exchange_execution_time_even_if_local_clock_differs():
    engine = TradingEngine(exchange=None, stream=None, order=None)
    symbol = Symbol('BTCUSDT')
    execution = Timestamp(datetime(2026, 1, 15, 12, tzinfo=timezone.utc))
    order = Order('test-trader', symbol, Side.BUY, Quantity(Decimal('1')), Price(Decimal('100')))
    response = OrderResponse('1', symbol, order.quantity, order.price, Side.BUY, TradeStatus.EXECUTED, execution)

    async def opened(trader_id, position):
        engine._running = False

    manager = SimpleNamespace(open_position=AsyncMock(side_effect=opened))
    engine._portfolio_manager = manager
    engine._running = True
    await engine._response_queue.put((order, response))
    await asyncio.wait_for(engine._portfolio_updater(), timeout=1)
    saved_position = manager.open_position.call_args.args[1]
    assert saved_position.entry_time == execution
    assert saved_position.to_dict()['entry_time'].endswith('+00:00')


def test_database_record_retains_utc_when_serialized():
    instant = datetime(2026, 7, 15, 14, tzinfo=timezone(timedelta(hours=2)))
    candle = PostgresAdapter('unused')._convert_to_candle_static({
        'symbol': 'BTCUSDT', 'interval': '1m', 'open_time': instant,
        'open': Decimal('100'), 'high': Decimal('110'), 'low': Decimal('90'),
        'close': Decimal('105'), 'volume': Decimal('2'),
    })
    assert CandleController().serialize_candle(candle)['open_time'] == '2026-07-15T12:00:00+00:00'
