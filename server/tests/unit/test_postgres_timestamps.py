"""Optional real PostgreSQL regression; uses and removes only an isolated schema."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from decimal import Decimal

import asyncpg
import pytest

from modules.trading.domain.entities import Position, OrderResponse
from modules.trading.domain.value_objects import Interval, Side, Symbol, TradeStatus, Price
from modules.trading.domain.aggregates import Portfolio, Trader
from modules.trading.application.services.portfolio_manager import PortfolioManager
from modules.trading.application.services.strategy_factory import StrategyFactory
from modules.trading.infrastructure.binance_adapter import BinanceAdapter
from modules.trading.infrastructure.postgre_adapter import PostgresAdapter
from modules.trading.infrastructure.postgres_portfolio_adapter import PostgresPortfolioAdapter
from scripts.migrate_utc import migrate


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Set TEST_DATABASE_URL for PostgreSQL regression')
async def test_postgres_roundtrip_latest_window_and_legacy_migration():
    url = os.environ['TEST_DATABASE_URL']
    schema = 'test_utc_' + uuid4().hex
    connection = await asyncpg.connect(url)
    adapter = PostgresAdapter(url)
    try:
        await connection.execute(f'CREATE SCHEMA {schema}')
        await connection.execute(f'SET search_path TO {schema}')
        init_sql = Path(__file__).resolve().parents[3] / 'docker' / 'init.sql'
        await connection.execute(init_sql.read_text(encoding='utf-8'))
        adapter._pool = await asyncpg.create_pool(url, min_size=1, max_size=2, server_settings={
            'search_path': schema, 'timezone': 'America/New_York',
        })
        symbol = Symbol('BTCUSDT')
        origin = datetime(2026, 7, 15, 12, tzinfo=timezone.utc)
        candles = [BinanceAdapter()._parse_candle(symbol, [
            int((origin + timedelta(minutes=i)).timestamp() * 1000), '100', '110', '90', '105', '2',
        ], Interval.M1) for i in range(3)]
        await adapter.save_candles(candles)
        result = await adapter.get_candles(symbol, Interval.M1, 2)
        assert [c.timestamp for c in result] == [c.timestamp for c in candles[-2:]]
        assert (await adapter.get_last_candle(symbol, Interval.M1)).timestamp == candles[-1].timestamp

        await connection.execute("INSERT INTO portfolios(id, name, initial_capital) VALUES ('p', 'test', 1000)")
        await connection.execute("INSERT INTO portfolio_traders (portfolio_id, trader_id, strategy_name, symbol, interval, allocated_capital) VALUES ('p', 't', 'mean_cross', 'BTCUSDT', '1m', 1000)")
        portfolios = PostgresPortfolioAdapter(url)
        portfolios._pool = adapter._pool
        position = Position(symbol, Side.BUY, candles[0].close, candles[0].timestamp, candles[0].volume, TradeStatus.EXECUTED)
        await portfolios.save_position('p', 't', position)
        assert (await portfolios.get_open_positions('p'))[0]['entry_time'] == origin
        trade = position.close(candles[-1].close, candles[-1].timestamp)
        await portfolios.save_trade('p', 't', trade)
        stored_trade = (await portfolios.get_trades('p', 't', 10))[0]
        assert stored_trade.entry_time == position.entry_time
        assert stored_trade.exit_time == candles[-1].timestamp

        # A configured strategy, cash remainder and completed trade survive reload.
        params = {'fast_period': 2, 'slow_period': 5}
        trader = Trader('configured', StrategyFactory.create_strategy('mean_cross', params), symbol, Interval.M1, strategy_params=params)
        portfolio = Portfolio('configured', 'configured', Decimal('1000'), [trader])
        manager = PortfolioManager(portfolios, portfolio)
        await manager.restore_state()
        loaded = await manager.load_portfolio('configured')
        assert loaded.num_traders == 1
        assert loaded.traders[0].strategy_params == params
        assert loaded.traders[0].strategy.min_candles_required == trader.strategy.min_candles_required
        await manager.open_position(trader.id, position)
        assert manager.get_capital(trader.id) == Decimal('790')
        await manager.load_portfolio('configured')
        assert manager.get_capital(trader.id) == Decimal('790')
        response = OrderResponse('test', symbol, position.quantity, Price(Decimal('110')), Side.SELL, TradeStatus.EXECUTED, candles[-1].timestamp)
        await manager.close_position(trader.id, response)
        loaded = await manager.load_portfolio('configured')
        assert not loaded.has_position(trader.id)
        assert loaded.get_capital(trader.id) == Decimal('1010')
        assert loaded.num_completed_trades(trader.id) == 1
        assert (await manager.get_trades_by_trader(trader.id))[0].pnl.value == Decimal('10')

        # Reconstruct the old schema's local wall times, then migrate without losing rows.
        await connection.execute("ALTER TABLE candles ALTER COLUMN open_time TYPE TIMESTAMP USING open_time AT TIME ZONE 'Europe/Madrid'")
        await migrate(connection, 'Europe/Madrid')
        await migrate(connection, 'Europe/Madrid')  # Already-aware columns are left untouched.
        stored = await connection.fetch('SELECT open_time FROM candles ORDER BY open_time')
        assert [row['open_time'] for row in stored] == [c.timestamp.timestamp for c in candles]
        with pytest.raises(ValueError, match='Unknown'):
            await migrate(connection, 'Invalid/Timezone')
    finally:
        await adapter.disconnect()
        # The only schema removed is the unique test schema created above.
        await connection.execute(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
        await connection.close()
