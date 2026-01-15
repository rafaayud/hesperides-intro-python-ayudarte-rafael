import pytest
import pytest_asyncio
import asyncio
import os
import uuid
from decimal import Decimal
from datetime import datetime

from src.trading.domain.value_objects import Symbol, Price, Timestamp, Quantity, Side, Interval
from src.trading.domain.entities import Trade, Position
from src.trading.domain.aggregates import Trader, Portfolio
from src.trading.infrastructure.postgres_portfolio_adapter import PostgresPortfolioAdapter
from src.api.config import get_settings


# ============================================================================
# FIXTURES
# ============================================================================

class MockStrategy:
    @property
    def name(self) -> str:
        return "mock_strategy"
    
    @property
    def min_candles_required(self) -> int:
        return 10


@pytest.fixture
def sample_symbol():
    return Symbol("BTCUSDT")


@pytest.fixture
def sample_timestamp():
    return Timestamp(datetime(2025, 1, 15, 12, 0, 0))


@pytest.fixture
def sample_position(sample_symbol, sample_timestamp):
    return Position(
        symbol=sample_symbol,
        side=Side.BUY,
        entry_price=Price(Decimal("50000.00")),
        quantity=Quantity(Decimal("0.1")),
        entry_time=sample_timestamp
    )


@pytest.fixture
def sample_trade(sample_symbol, sample_timestamp):
    return Trade(
        symbol=sample_symbol,
        entry_price=Price(Decimal("50000.00")),
        exit_price=Price(Decimal("52000.00")),
        entry_time=sample_timestamp,
        exit_time=Timestamp(datetime(2025, 1, 15, 14, 0, 0)),
        quantity=Quantity(Decimal("0.1"))
    )


@pytest.fixture
def sample_trader(sample_symbol):
    return Trader(
        id=str(uuid.uuid4()),
        strategy=MockStrategy(),
        symbol=sample_symbol,
        interval=Interval.H1
    )


@pytest.fixture
def sample_portfolio(sample_trader):
    return Portfolio(
        id=str(uuid.uuid4()),
        name="Test Portfolio",
        initial_capital=Decimal("100000.00"),
        traders=[sample_trader]
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# def get_db_url():
#     """Obtiene la URL de la base de datos para los tests"""
#     from src.api.config import get_settings
#     settings = get_settings()
#     return os.getenv("TEST_DATABASE_URL", settings.database_url)

async def cleanup_tables(adapter):
    """Limpia las tablas antes de un test"""
    async with adapter._pool.acquire() as conn:
        await conn.execute("DELETE FROM trades")
        await conn.execute("DELETE FROM positions")
        await conn.execute("DELETE FROM portfolio_traders")
        await conn.execute("DELETE FROM portfolios")


# ============================================================================
# INTEGRATION TESTS - Portfolio
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_retrieve_portfolio(sample_portfolio):
    """Verifica que se puede guardar y recuperar un portfolio correctamente"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        # Limpiar tablas antes del test
        await cleanup_tables(adapter)
        
        # Guardar portfolio
        await adapter.save_portfolio(sample_portfolio)
        
        # Recuperar y verificar
        data = await adapter.get_portfolio_data(sample_portfolio.id)
        assert data is not None, f"Portfolio {sample_portfolio.id} no se encontró en la base de datos"
        assert data["id"] == sample_portfolio.id
        assert data["name"] == sample_portfolio.name
        assert data["initial_capital"] == sample_portfolio.initial_capital
        assert len(data["traders"]) == 1
        assert data["traders"][0]["trader_id"] == sample_portfolio.traders[0].id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_portfolio_with_multiple_traders(sample_symbol):
    """Verifica que se guardan todos los traders de un portfolio"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    
    traders = [
        Trader(id=str(uuid.uuid4()), strategy=MockStrategy(), symbol=sample_symbol, interval=Interval.H1)
        for i in range(3)
    ]
    portfolio = Portfolio(
        id=str(uuid.uuid4()),
        name="Multi Trader",
        initial_capital=Decimal("300000.00"),
        traders=traders
    )
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(portfolio)
        
        data = await adapter.get_portfolio_data(portfolio.id)
        assert data is not None
        assert len(data["traders"]) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_portfolio_returns_none_when_not_found():
    """Verifica que retorna None si el portfolio no existe"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        result = await adapter.get_portfolio_data("nonexistent_id")
        assert result is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_portfolios(sample_portfolio):
    """Verifica que se pueden listar portfolios"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(sample_portfolio)
        
        portfolios = await adapter.list_portfolios()
        assert len(portfolios) >= 1
        assert any(p["id"] == sample_portfolio.id for p in portfolios)


# # ============================================================================
# # INTEGRATION TESTS - Position
# # ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_retrieve_position(sample_position):
    """Verifica que se puede guardar y recuperar una posición"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    portfolio_id = str(uuid.uuid4())
    trader_id = str(uuid.uuid4())
    
    # Crear portfolio y trader primero
    portfolio = Portfolio(
        id=portfolio_id,
        name="Test",
        initial_capital=Decimal("10000"),
        traders=[Trader(id=trader_id, strategy=MockStrategy(), 
                      symbol=Symbol("BTCUSDT"), interval=Interval.H1)]
    )
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(portfolio)
        
        # Guardar posición
        await adapter.save_position(portfolio_id, trader_id, sample_position)
        
        # Recuperar posiciones
        positions = await adapter.get_open_positions(portfolio_id)
        assert len(positions) == 1
        assert positions[0]["symbol"] == "BTCUSDT"
        assert positions[0]["side"] == "BUY"
        assert positions[0]["entry_price"] == Decimal("50000.00")
        assert positions[0]["quantity"] == Decimal("0.1")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_position(sample_position):
    """Verifica que se puede eliminar una posición"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    portfolio_id = str(uuid.uuid4())
    trader_id = str(uuid.uuid4())
    
    # Setup
    portfolio = Portfolio(
        id=portfolio_id,
        name="Test Delete",
        initial_capital=Decimal("10000"),
        traders=[Trader(id=trader_id, strategy=MockStrategy(),
                      symbol=Symbol("BTCUSDT"), interval=Interval.H1)]
    )
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(portfolio)
        
        # Abrir posición
        await adapter.save_position(portfolio_id, trader_id, sample_position)
        positions = await adapter.get_open_positions(portfolio_id)
        assert len(positions) == 1
        
        # Cerrar posición
        await adapter.delete_positions(portfolio_id, trader_id)
        positions = await adapter.get_open_positions(portfolio_id)
        assert len(positions) == 0


# # ============================================================================
# # INTEGRATION TESTS - Trade
# # ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_retrieve_trade(sample_trade):
    """Verifica que se puede guardar y recuperar un trade"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    portfolio_id = str(uuid.uuid4())
    trader_id = str(uuid.uuid4())
    
    # Setup
    portfolio = Portfolio(
        id=portfolio_id,
        name="Trade Test",
        initial_capital=Decimal("10000"),
        traders=[Trader(id=trader_id, strategy=MockStrategy(),
                      symbol=Symbol("BTCUSDT"), interval=Interval.H1)]
    )
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(portfolio)
        
        # Guardar trade
        await adapter.save_trade(portfolio_id, trader_id, sample_trade)
        
        # Recuperar trades
        trades = await adapter.get_trades(portfolio_id)
        assert len(trades) == 1
        assert isinstance(trades[0], Trade)
        assert trades[0].symbol.symbol == "BTCUSDT"
        assert trades[0].entry_price.value == Decimal("50000.00")
        assert trades[0].exit_price.value == Decimal("52000.00")
        assert trades[0].quantity.value == Decimal("0.1")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_trades_with_trader_filter(sample_trade):
    """Verifica que se pueden filtrar trades por trader"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    portfolio_id = str(uuid.uuid4())
    trader1_id = str(uuid.uuid4())
    trader2_id = str(uuid.uuid4())
    
    # Setup con 2 traders
    portfolio = Portfolio(
        id=portfolio_id,
        name="Filter Test",
        initial_capital=Decimal("20000"),
        traders=[
            Trader(id=trader1_id, strategy=MockStrategy(), symbol=Symbol("BTCUSDT"), interval=Interval.H1),
            Trader(id=trader2_id, strategy=MockStrategy(), symbol=Symbol("ETHUSDT"), interval=Interval.H1)
        ]
    )
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(portfolio)
        
        # Guardar trade para trader 1
        await adapter.save_trade(portfolio_id, trader1_id, sample_trade)
        
        # Recuperar solo trades del trader 1
        trades = await adapter.get_trades(portfolio_id, trader_id=trader1_id)
        assert len(trades) == 1
        
        # Recuperar todos los trades
        all_trades = await adapter.get_trades(portfolio_id)
        assert len(all_trades) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_portfolio_pnl(sample_trade):
    """Verifica que se calcula correctamente el PnL total del portfolio"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    portfolio_id = str(uuid.uuid4())
    trader_id = str(uuid.uuid4())
    
    # Setup
    portfolio = Portfolio(
        id=portfolio_id,
        name="PnL Test",
        initial_capital=Decimal("10000"),
        traders=[Trader(id=trader_id, strategy=MockStrategy(),
                      symbol=Symbol("BTCUSDT"), interval=Interval.H1)]
    )
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(portfolio)
        
        # Guardar trade con ganancia: (52000 - 50000) * 0.1 = 200
        await adapter.save_trade(portfolio_id, trader_id, sample_trade)
        
        # Verificar PnL total
        pnl = await adapter.get_portfolio_pnl(portfolio_id)
        expected_pnl = (sample_trade.exit_price.value - sample_trade.entry_price.value) * sample_trade.quantity.value
        assert pnl.value == expected_pnl
        assert pnl.value == Decimal("200.00")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_portfolio_pnl_with_multiple_trades():
    """Verifica cálculo de PnL con múltiples trades"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    portfolio_id = str(uuid.uuid4())
    trader_id = str(uuid.uuid4())
    
    # Setup
    portfolio = Portfolio(
        id=portfolio_id,
        name="Multi Trade PnL",
        initial_capital=Decimal("10000"),
        traders=[Trader(id=trader_id, strategy=MockStrategy(),
                      symbol=Symbol("BTCUSDT"), interval=Interval.H1)]
    )
    
    # Guardar varios trades
    trades = [
        Trade(
            symbol=Symbol("BTCUSDT"),
            entry_price=Price(Decimal("50000")),
            exit_price=Price(Decimal("51000")),  # +1000
            entry_time=Timestamp(datetime(2025, 1, 15, 12, 0)),
            exit_time=Timestamp(datetime(2025, 1, 15, 13, 0)),
            quantity=Quantity(Decimal("0.1"))  # PnL: +100
        ),
        Trade(
            symbol=Symbol("BTCUSDT"),
            entry_price=Price(Decimal("50000")),
            exit_price=Price(Decimal("49000")),  # -1000
            entry_time=Timestamp(datetime(2025, 1, 15, 14, 0)),
            exit_time=Timestamp(datetime(2025, 1, 15, 15, 0)),
            quantity=Quantity(Decimal("0.1"))  # PnL: -100
        ),
    ]
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(portfolio)
        
        for trade in trades:
            await adapter.save_trade(portfolio_id, trader_id, trade)
        
        # PnL total debería ser 0 (100 - 100)
        pnl = await adapter.get_portfolio_pnl(portfolio_id)
        assert pnl.value == Decimal("0")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_portfolio_pnl_returns_zero_when_no_trades(sample_portfolio):
    """Verifica que retorna 0 cuando no hay trades"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(sample_portfolio)
        
        pnl = await adapter.get_portfolio_pnl(sample_portfolio.id)
        assert pnl.value == Decimal("0")


# ============================================================================
# INTEGRATION TESTS - Full Lifecycle
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_trading_lifecycle(sample_position, sample_trade):
    """Test completo: portfolio -> abrir posición -> cerrar posición -> guardar trade"""
    from src.api.config import get_settings
    settings = get_settings()
    db_url = settings.database_url
    
    portfolio_id = str(uuid.uuid4())
    trader_id = str(uuid.uuid4())
    
    # 1. Crear portfolio
    portfolio = Portfolio(
        id=portfolio_id,
        name="Lifecycle Test",
        initial_capital=Decimal("10000"),
        traders=[Trader(id=trader_id, strategy=MockStrategy(),
                      symbol=Symbol("BTCUSDT"), interval=Interval.H1)]
    )
    
    async with PostgresPortfolioAdapter(db_url) as adapter:
        await cleanup_tables(adapter)
        await adapter.save_portfolio(portfolio)
        
        # 2. Abrir posición
        await adapter.save_position(portfolio_id, trader_id, sample_position)
        positions = await adapter.get_open_positions(portfolio_id)
        assert len(positions) == 1
        
        # 3. Cerrar posición
        await adapter.delete_positions(portfolio_id, trader_id)
        positions = await adapter.get_open_positions(portfolio_id)
        assert len(positions) == 0
        
        # 4. Guardar trade
        await adapter.save_trade(portfolio_id, trader_id, sample_trade)
        trades = await adapter.get_trades(portfolio_id)
        assert len(trades) == 1
        
        # 5. Verificar PnL
        pnl = await adapter.get_portfolio_pnl(portfolio_id)
        assert pnl.value == Decimal("200.00")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
