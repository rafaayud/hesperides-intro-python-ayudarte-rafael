-- =============================================================================
-- TRADING PLATFORM - DATABASE INITIALIZATION SCRIPT
-- =============================================================================
-- Este script se ejecuta automáticamente al iniciar el contenedor PostgreSQL
-- Crea todas las tablas necesarias para la plataforma de trading
-- =============================================================================

-- =============================================================================
-- TABLA: candles (datos de mercado históricos)
-- =============================================================================
CREATE TABLE candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume NUMERIC,
    UNIQUE (symbol, interval, open_time)
);

-- =============================================================================
-- TABLA: portfolios (carteras de trading)
-- =============================================================================
CREATE TABLE portfolios (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(100) NOT NULL UNIQUE,
    initial_capital NUMERIC(18,8) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- TABLA: portfolio_traders (traders asignados a portfolios)
-- =============================================================================
CREATE TABLE portfolio_traders (
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    trader_id TEXT NOT NULL,
    strategy_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    allocated_capital NUMERIC(18,8) NOT NULL,
    strategy_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (portfolio_id, trader_id)
);

-- =============================================================================
-- TABLA: positions (posiciones abiertas)
-- =============================================================================
CREATE TABLE positions (
    portfolio_id TEXT REFERENCES portfolios(id) ON DELETE CASCADE,
    trader_id TEXT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    entry_price NUMERIC(18,8) NOT NULL,
    quantity NUMERIC(18,8) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'OPEN',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (portfolio_id, trader_id),
    FOREIGN KEY (portfolio_id, trader_id) REFERENCES portfolio_traders(portfolio_id, trader_id) ON DELETE CASCADE
);

-- =============================================================================
-- TABLA: trades (operaciones cerradas)
-- =============================================================================
CREATE TABLE trades (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    portfolio_id TEXT REFERENCES portfolios(id),
    trader_id TEXT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    entry_price NUMERIC(18,8) NOT NULL,
    exit_price NUMERIC(18,8) NOT NULL,
    quantity NUMERIC(18,8) NOT NULL,
    pnl NUMERIC(18,8) NOT NULL,
    pnl_percentage NUMERIC(8,4) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- ÍNDICES para optimizar queries
-- =============================================================================
CREATE INDEX idx_candles_lookup ON candles(symbol, interval, open_time);
CREATE INDEX idx_candles_symbol_interval ON candles(symbol, interval);
CREATE INDEX idx_positions_portfolio ON positions(portfolio_id);
CREATE INDEX idx_trades_portfolio ON trades(portfolio_id);
CREATE INDEX idx_trades_trader ON trades(portfolio_id, trader_id);
CREATE INDEX idx_trades_time ON trades(exit_time DESC);

-- =============================================================================
-- MENSAJE DE CONFIRMACIÓN
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Base de datos inicializada correctamente';
    RAISE NOTICE '   - Tabla candles creada';
    RAISE NOTICE '   - Tabla portfolios creada';
    RAISE NOTICE '   - Tabla portfolio_traders creada';
    RAISE NOTICE '   - Tabla positions creada';
    RAISE NOTICE '   - Tabla trades creada';
    RAISE NOTICE '   - Índices creados';
END $$;

