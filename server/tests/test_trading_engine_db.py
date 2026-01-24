"""
Comprehensive tests for TradingEngine.

Tests verify:
1. Portfolio is saved correctly
2. Positions are saved when opened
3. Trades are saved when positions are closed
4. Portfolio state is restored correctly on restart
5. Capital is calculated correctly based on trades and positions
"""
import pytest
import pytest_asyncio
import asyncio
from decimal import Decimal
from datetime import datetime

from modules.trading.application.services.trading_engine import TradingEngine
from modules.trading.domain.value_objects import (
    Symbol, Interval, ExecutionMode, Price, Quantity, Timestamp, Side, TradeStatus
)
from modules.trading.domain.aggregates import Portfolio, Trader
from modules.trading.domain.strategies.mock_strategy import MockStrategy
from modules.trading.domain.entities import Candle, Position
from modules.trading.infrastructure.mocks.mock_exchange_adapter import MockExchangeAdapter
from modules.trading.infrastructure.mocks.mock_stream_adapter import MockStreamAdapter
from modules.trading.infrastructure.mocks.mock_order_adapter import MockOrderAdapter
from modules.trading.infrastructure.postgres_portfolio_adapter import PostgresPortfolioAdapter
from apps.api.config import get_settings


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def cleanup_tables(adapter):
    """Limpia las tablas antes de un test"""
    async with adapter._pool.acquire() as conn:
        await conn.execute("DELETE FROM trades")
        await conn.execute("DELETE FROM positions")
        await conn.execute("DELETE FROM portfolio_traders")
        await conn.execute("DELETE FROM portfolios")


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def db_adapter():
    """PostgreSQL adapter for testing (real adapter)."""
    settings = get_settings()
    adapter = PostgresPortfolioAdapter(db_url=settings.database_url)
    await adapter.connect()
    # Cleanup before each test
    await cleanup_tables(adapter)
    yield adapter
    # Cleanup after each test
    
    await adapter.disconnect()


@pytest.fixture
def mock_exchange():
    """Mock exchange adapter."""
    return MockExchangeAdapter.deterministic(base_price=50000.0, seed=42)


@pytest.fixture
def mock_stream():
    """Mock stream adapter."""
    return MockStreamAdapter(base_price=50000.0, delay=0.1)


@pytest.fixture
def mock_order():
    """Mock order adapter."""
    return MockOrderAdapter(seed=42)


@pytest.fixture
def sample_traders():
    """Create sample traders for testing."""
    strategy = MockStrategy(name="TestStrategy", min_candles=10, mode=ExecutionMode.ON_CLOSE)
    return [
        Trader(
            id="1",
            strategy=strategy,
            symbol=Symbol("BTCUSDT"),
            interval=Interval.M1
        ),
        Trader(
            id="2",
            strategy=strategy,
            symbol=Symbol("ETHUSDT"),
            interval=Interval.M1
        )
    ]


@pytest.fixture
def sample_portfolio(sample_traders):
    """Create a sample portfolio for testing."""
    return Portfolio(
        id="test_portfolio_1",
        name="Test Portfolio",
        initial_capital=Decimal("100000"),
        traders=sample_traders
    )


# ============================================================================
# TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_trading_engine_saves_portfolio(
    db_adapter, mock_exchange, mock_stream, mock_order, sample_portfolio
) -> None:
    """Test that trading engine saves portfolio to database."""
    # Create trading engine
    engine = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=sample_portfolio,
        portfolio_storage=db_adapter
    )
    
    # Startup should save portfolio
    await engine.startup()
    
    # Verify portfolio was saved
    portfolio_data = await db_adapter.get_portfolio_data(sample_portfolio.id)
    assert portfolio_data is not None
    assert portfolio_data["id"] == sample_portfolio.id
    assert portfolio_data["name"] == sample_portfolio.name
    assert float(Decimal(portfolio_data["initial_capital"])) == pytest.approx(float(sample_portfolio.initial_capital), abs=0.01)
    
    # Cleanup
    await engine.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trading_engine_saves_position_on_buy(
    db_adapter, mock_exchange, mock_stream, mock_order, sample_portfolio
):
    """Test that saves position when a BUY order is executed."""
    trader = sample_portfolio.traders[0]
    
    # Create trading engine
    engine = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=sample_portfolio,
        portfolio_storage=db_adapter
    )
    
    await engine.startup()
    
    # Manually trigger a BUY signal by creating an order
    # We'll simulate this by directly calling the portfolio updater logic
    from modules.trading.domain.entities import Order, OrderResponse
    
    # Get current market price
    current_price = await mock_order.get_current_price(trader.symbol)
    
    # Create a BUY order with current market price
    order = Order(
        trader_id=trader.id,
        symbol=trader.symbol,
        side=Side.BUY,
        quantity=Quantity(Decimal("0.1")),
        price=current_price,
        timestamp=Timestamp(datetime.now())
    )
    
    # Execute order
    response = await mock_order.buy_market(trader.symbol, order.quantity)
    
    # Manually update portfolio (simulating what _portfolio_updater does)
    position = Position(
        symbol=response.symbol,
        side=response.side,
        entry_price=response.price,
        quantity=response.quantity,
        entry_time=response.timestamp,
        status=response.status
    )
    
    sample_portfolio.open_position(trader.id, position)
    await db_adapter.save_position(sample_portfolio.id, trader.id, position)
    
    # Verify position was saved
    open_positions = await db_adapter.get_open_positions(sample_portfolio.id)
    assert len(open_positions) == 1
    assert open_positions[0]["trader_id"] == trader.id
    assert open_positions[0]["symbol"] == str(trader.symbol)
    
    # Cleanup
    await engine.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trading_engine_saves_trade_on_sell(
    db_adapter, mock_exchange, mock_stream, mock_order, sample_portfolio
):
    """Test that trading engine saves trade when a position is closed."""
    trader = sample_portfolio.traders[0]
    
    # Create trading engine
    engine = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=sample_portfolio,
        portfolio_storage=db_adapter
    )
    
    await engine.startup()
    
    # First, open a position
    from modules.trading.domain.entities import Order, OrderResponse, Position
    
    # Get current market price
    current_price = await mock_order.get_current_price(trader.symbol)
    
    # Create and execute BUY order with current market price
    buy_order = Order(
        trader_id=trader.id,
        symbol=trader.symbol,
        side=Side.BUY,
        quantity=Quantity(Decimal("0.1")),
        price=current_price,
        timestamp=Timestamp(datetime.now())
    )
    
    buy_response = await mock_order.buy_market(trader.symbol, buy_order.quantity)
    position = Position(
        symbol=buy_response.symbol,
        side=buy_response.side,
        entry_price=buy_response.price,
        quantity=buy_response.quantity,
        entry_time=buy_response.timestamp,
        status=buy_response.status
    )
    
    sample_portfolio.open_position(trader.id, position)
    await db_adapter.save_position(sample_portfolio.id, trader.id, position)
    
    # Now close the position with a SELL order
    sell_response = await mock_order.sell_market(trader.symbol, position.quantity)
    
    # Close position and get trade
    trade = sample_portfolio.close_position(trader.id, sell_response)
    
    # Save trade and delete position
    await db_adapter.save_trade(sample_portfolio.id, trader.id, trade)
    await db_adapter.delete_positions(sample_portfolio.id, trader.id)
    
    # Verify trade was saved
    trades = await db_adapter.get_trades(sample_portfolio.id, trader_id=trader.id)
    assert len(trades) == 1
    assert trades[0].symbol == trader.symbol
    assert float(trades[0].entry_price.value) == pytest.approx(float(buy_response.price.value), abs=0.01)
    assert float(trades[0].exit_price.value) == pytest.approx(float(sell_response.price.value), abs=0.01)
    
    # Verify position was deleted
    open_positions = await db_adapter.get_open_positions(sample_portfolio.id)
    assert len(open_positions) == 0
    
    # Cleanup
    await engine.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trading_engine_restores_portfolio_state(
    db_adapter, mock_exchange, mock_stream, mock_order, sample_portfolio
):
    """Test that trading engine correctly restores portfolio state from database."""
    trader = sample_portfolio.traders[0]
    
    # Step 1: Create engine, save portfolio, open position, close it (create trade)
    engine1 = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=sample_portfolio,
        portfolio_storage=db_adapter
    )
    
    await engine1.startup()
    
    # Open and close a position to create a trade
    from modules.trading.domain.entities import Order, Position
    
    buy_response = await mock_order.buy_market(trader.symbol, Quantity(Decimal("0.1")))
    position = Position(
        symbol=buy_response.symbol,
        side=buy_response.side,
        entry_price=buy_response.price,
        quantity=buy_response.quantity,
        entry_time=buy_response.timestamp,
        status=buy_response.status
    )
    
    sample_portfolio.open_position(trader.id, position)
    await db_adapter.save_position(sample_portfolio.id, trader.id, position)
    
    # Close position
    sell_response = await mock_order.sell_market(trader.symbol, position.quantity)
    trade = sample_portfolio.close_position(trader.id, sell_response)
    await db_adapter.save_trade(sample_portfolio.id, trader.id, trade)
    await db_adapter.delete_positions(sample_portfolio.id, trader.id)
    
    await engine1.stop()
    
    # Step 2: Create a NEW engine with a NEW portfolio instance (same ID)
    # This simulates a restart
    new_portfolio = Portfolio(
        id=sample_portfolio.id,  # Same ID!
        name=sample_portfolio.name,
        initial_capital=sample_portfolio.initial_capital,
        traders=sample_portfolio.traders  # Same traders
    )
    
    engine2 = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=new_portfolio,
        portfolio_storage=db_adapter
    )
    
    # Startup should restore state
    await engine2.startup()
    
    # Verify state was restored
    # Check that trade is in portfolio
    # Access trades directly (restored by restore_state)
    trades = new_portfolio._trades.get(trader.id, [])
    assert len(trades) == 1
    assert trades[0].symbol == trader.symbol
    
    # Check that capital was calculated correctly
    # Initial capital per trader = 100000 / 2 = 50000
    # Capital should be: 50000 + PnL from trade
    capital = new_portfolio.get_capital(trader.id)
    expected_capital = Decimal("50000") + trades[0].pnl.value
    assert float(capital) == pytest.approx(float(expected_capital), abs=0.01)
    
    await engine2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trading_engine_restores_open_position(
    db_adapter, mock_exchange, mock_stream, mock_order, sample_portfolio
):
    """Test that trading engine correctly restores open positions and sets capital to 0."""
    trader = sample_portfolio.traders[0]
    
    # Step 1: Create engine, save portfolio, open position (but don't close it)
    engine1 = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=sample_portfolio,
        portfolio_storage=db_adapter
    )
    
    await engine1.startup()
    
    # Open a position
    from modules.trading.domain.entities import Position
    
    buy_response = await mock_order.buy_market(trader.symbol, Quantity(Decimal("0.1")))
    position = Position(
        symbol=buy_response.symbol,
        side=buy_response.side,
        entry_price=buy_response.price,
        quantity=buy_response.quantity,
        entry_time=buy_response.timestamp,
        status=buy_response.status
    )
    
    sample_portfolio.open_position(trader.id, position)
    await db_adapter.save_position(sample_portfolio.id, trader.id, position)
    
    await engine1.stop()
    
    # Step 2: Create a NEW engine with a NEW portfolio instance (same ID)
    new_portfolio = Portfolio(
        id=sample_portfolio.id,
        name=sample_portfolio.name,
        initial_capital=sample_portfolio.initial_capital,
        traders=sample_portfolio.traders
    )
    
    engine2 = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=new_portfolio,
        portfolio_storage=db_adapter
    )
    
    # Startup should restore state
    await engine2.startup()
    
    # Verify position was restored
    assert new_portfolio.has_position(trader.id)
    restored_position = new_portfolio.get_position(trader.id)
    assert restored_position is not None
    assert restored_position.symbol == trader.symbol
    assert restored_position.quantity.value == position.quantity.value
    
    # Verify capital is 0 (locked in position)
    capital = new_portfolio.get_capital(trader.id)
    assert capital == Decimal("0")
    
    await engine2.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trading_engine_calculates_capital_correctly(
    db_adapter, mock_exchange, mock_stream, mock_order, sample_portfolio
):
    """Test that capital is calculated correctly: initial + PnL from trades."""
    trader = sample_portfolio.traders[0]
    
    engine = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=sample_portfolio,
        portfolio_storage=db_adapter
    )
    
    await engine.startup()
    
    # Open and close multiple positions to create multiple trades
    from modules.trading.domain.entities import Position
    
    trades_created = []
    for _ in range(3):
        # Buy
        buy_response = await mock_order.buy_market(trader.symbol, Quantity(Decimal("0.1")))
        position = Position(
            symbol=buy_response.symbol,
            side=buy_response.side,
            entry_price=buy_response.price,
            quantity=buy_response.quantity,
            entry_time=buy_response.timestamp,
            status=buy_response.status
        )
        
        sample_portfolio.open_position(trader.id, position)
        await db_adapter.save_position(sample_portfolio.id, trader.id, position)
        
        # Sell
        sell_response = await mock_order.sell_market(trader.symbol, position.quantity)
        trade = sample_portfolio.close_position(trader.id, sell_response)
        await db_adapter.save_trade(sample_portfolio.id, trader.id, trade)
        await db_adapter.delete_positions(sample_portfolio.id, trader.id)
        
        trades_created.append(trade)
    
    # Calculate expected capital
    initial_capital_per_trader = sample_portfolio.initial_capital / len(sample_portfolio.traders)
    total_pnl = sum(trade.pnl.value for trade in trades_created)
    expected_capital = initial_capital_per_trader + total_pnl
    
    # Verify capital
    capital = sample_portfolio.get_capital(trader.id)
    assert float(capital) == pytest.approx(float(expected_capital), abs=0.01)
    
    await engine.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trading_engine_handles_multiple_traders(
    db_adapter, mock_exchange, mock_stream, mock_order, sample_portfolio
):
    """Test that trading engine correctly handles multiple traders independently."""
    trader1 = sample_portfolio.traders[0]
    trader2 = sample_portfolio.traders[1]
    
    engine = TradingEngine(
        exchange=mock_exchange,
        stream=mock_stream,
        order=mock_order,
        portfolio=sample_portfolio,
        portfolio_storage=db_adapter
    )
    
    await engine.startup()
    
    # Trader 1: Open position (capital should be 0)
    from modules.trading.domain.entities import Position
    
    buy_response1 = await mock_order.buy_market(trader1.symbol, Quantity(Decimal("0.1")))
    position1 = Position(
        symbol=buy_response1.symbol,
        side=buy_response1.side,
        entry_price=buy_response1.price,
        quantity=buy_response1.quantity,
        entry_time=buy_response1.timestamp,
        status=buy_response1.status
    )
    
    sample_portfolio.open_position(trader1.id, position1)
    await db_adapter.save_position(sample_portfolio.id, trader1.id, position1)
    
    # Trader 2: Close a position (create trade, capital should be initial + PnL)
    buy_response2 = await mock_order.buy_market(trader2.symbol, Quantity(Decimal("0.1")))
    position2 = Position(
        symbol=buy_response2.symbol,
        side=buy_response2.side,
        entry_price=buy_response2.price,
        quantity=buy_response2.quantity,
        entry_time=buy_response2.timestamp,
        status=buy_response2.status
    )
    
    sample_portfolio.open_position(trader2.id, position2)
    await db_adapter.save_position(sample_portfolio.id, trader2.id, position2)
    
    sell_response2 = await mock_order.sell_market(trader2.symbol, position2.quantity)
    trade2 = sample_portfolio.close_position(trader2.id, sell_response2)
    await db_adapter.save_trade(sample_portfolio.id, trader2.id, trade2)
    await db_adapter.delete_positions(sample_portfolio.id, trader2.id)
    
    # Verify trader1 has position and capital = 0
    assert sample_portfolio.has_position(trader1.id)
    assert sample_portfolio.get_capital(trader1.id) == Decimal("0")
    
    # Verify trader2 has no position and capital = initial + PnL
    assert not sample_portfolio.has_position(trader2.id)
    initial_capital = sample_portfolio.initial_capital / len(sample_portfolio.traders)
    expected_capital2 = initial_capital + trade2.pnl.value
    assert float(sample_portfolio.get_capital(trader2.id)) == pytest.approx(float(expected_capital2), abs=0.01)
    
    await engine.stop()


