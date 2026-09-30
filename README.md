# CryptoTrader

**An educational cryptocurrency trading engine built with hexagonal architecture, FastAPI and React.**

[![CI](https://github.com/rafaayud/hesperides-intro-python-ayudarte-rafael/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/rafaayud/hesperides-intro-python-ayudarte-rafael/actions/workflows/ci.yml)

Built in January-February 2026 as a university project to learn how domain logic, application services and external integrations fit together. CryptoTrader combines live Binance market data, local backtesting, portfolio management and order execution on **Binance Spot Testnet**.

[Original academic report (Spanish)](docs/memoria.pdf) · [Domain and services](server/modules/trading) · [Frontend](client/src) · [Tests](server/tests)

## Features

- Live OHLCV candlestick and volume charts, streamed over WebSocket and backed by PostgreSQL history.
- Moving average crossover, crossover with take profit, momentum and a random test strategy.
- Backtests with entry/exit markers, trade history, realized PnL and win rate.
- Portfolios containing multiple traders, each with its own symbol, interval and saved strategy parameters.
- An asynchronous trading pipeline connecting market events, signals, orders and portfolio updates.
- Consistent UTC timestamps across exchange responses, storage, charts, tables and the dashboard clock.

Public market data and backtesting work **without API keys**. Starting a trading engine requires Spot Testnet credentials. Backtesting is a local simulation; Testnet submits orders to Binance's separate test environment.

## Screenshots

![Live market chart and completed Testnet trade](docs/screenshots/trading.png)

![Backtest configuration, chart and results](docs/screenshots/backtest.png)

![Portfolio and trade history](docs/screenshots/portfolio.png)

## Quick start

Requires Git, Docker and Docker Compose.

```bash
git clone https://github.com/rafaayud/hesperides-intro-python-ayudarte-rafael.git
cd hesperides-intro-python-ayudarte-rafael
docker compose up --build -d
```

The first run installs dependencies and initializes the database.

| Service | Local address |
| --- | --- |
| Dashboard | http://localhost:5173 |
| Interactive API documentation | http://localhost:8000/docs |
| API health | http://localhost:8000/health |
| PostgreSQL | `localhost:5432` |

1. Open **Trading**, select BTC/USDT and `1h`, and wait for history to synchronize.
2. Open **Backtest**, choose *Moving Average Cross*, and run the simulation. Chart markers and trade timestamps use UTC. Scroll or zoom the chart to explore earlier trades.
3. Open **Portfolios** to create a portfolio and configure its traders. Add Testnet credentials before pressing **Start**. **Stop** stops the engine; it does not liquidate an open position.

```bash
docker compose logs -f trading_app
docker compose down
```

Database data survives container restarts in the `postgres_data` volume. **`docker compose down -v` deletes that volume and its data.** Compose binds ports to the local computer only.

### Spot Testnet configuration

Copy `.env.example` to `.env` (`cp .env.example .env` on macOS/Linux, or `Copy-Item .env.example .env` in PowerShell). Add credentials from [Binance Spot Testnet](https://testnet.binance.vision/), then run `docker compose up -d` again.

| Variable | Purpose | Example/default |
| --- | --- | --- |
| `BINANCE_API_KEY` | Spot Testnet API key | Empty |
| `BINANCE_SECRET_KEY` | Spot Testnet secret | Empty |
| `BINANCE_TESTNET` | Test environment setting | `true` |
| `DATABASE_URL` | Database URL for a backend outside Docker | `postgresql://postgres:postgres@localhost:5432/trading` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Local Compose database | `postgres` / `postgres` / `trading` |
| `VITE_API_URL` | Frontend API base URL | `http://localhost:8000/api` |

Compose sets its backend database URL using the internal `postgres` hostname. `.env` is excluded from Git and Docker build context; only the empty example belongs in the repository.

## Architecture

The domain owns the trading rules and port interfaces. Application services orchestrate use cases. Infrastructure adapters implement those ports, and FastAPI wires dependencies at startup. The React dashboard communicates with the API through REST and WebSocket endpoints.

```mermaid
flowchart LR
    UI[React dashboard] --> API[FastAPI controllers]
    subgraph Core[Application core]
        Services[Application services] --> Domain[Portfolios, traders and strategies]
        Services --> Ports[Domain port interfaces]
    end
    API --> Services
    Binance[Binance adapters] -. implement .-> Ports
    Postgres[PostgreSQL adapters] -. implement .-> Ports
    Mocks[Test adapters] -. implement .-> Ports
    Binance --> Public[Public market data]
    Binance --> Testnet[Spot Testnet orders]
    Postgres --> DB[(PostgreSQL)]
```

| Layer | Responsibility | Examples |
| --- | --- | --- |
| Domain | Entities, value objects, aggregates, strategies and ports | `Timestamp`, `CandleBuffer`, `Trader`, `Portfolio`, `ExchangePort` |
| Application | Data ingestion, backtesting, portfolio state and execution | `DataIngestionService`, `BacktestService`, `PortfolioManager`, `TradingEngine` |
| Infrastructure | Market data, order execution and persistence | `BinanceAdapter`, `BinanceStreamAdapter`, `BinanceOrderAdapter`, `PostgresPortfolioAdapter` |
| Entry points | HTTP routes, request validation and dependency setup | `server/apps/api` |

### Trading pipeline

Four asynchronous tasks communicate through three bounded `asyncio.Queue` instances. Traders sharing a symbol and interval receive the same candle stream.

```mermaid
flowchart LR
    Stream[WebSocket task] --> CQ[Candle queue]
    CQ --> Signals[Signal processor]
    Signals --> OQ[Order queue]
    OQ --> Orders[Order executor]
    Orders --> RQ[Response queue]
    RQ --> Update[Portfolio updater]
    Update --> DB[(Positions and trades)]
```

### A completed trade

```mermaid
sequenceDiagram
    participant Market as Market stream
    participant Trader
    participant Engine as Trading engine
    participant Exchange as Spot Testnet
    participant Portfolio
    participant DB as PostgreSQL
    Market->>Trader: Closed candle
    Trader->>Engine: BUY signal
    Engine->>Exchange: Market buy
    Exchange-->>Engine: Fill price, quantity and UTC execution time
    Engine->>Portfolio: Open position
    Portfolio->>DB: Save open position
    Market->>Trader: Later closed candle
    Trader->>Engine: SELL signal
    Engine->>Exchange: Market sell
    Exchange-->>Engine: Fill and UTC execution time
    Engine->>Portfolio: Close position and calculate realized PnL
    Portfolio->>DB: Save trade and remove open position
```

Prices and quantities use `Decimal`. Connections use asynchronous context managers. Strategies can be exercised with historical candles and test adapters without sending exchange orders.

```text
client/
  src/components/             Trading, portfolios and backtesting UI
  src/lib/                    API client and shared chart time handling
  tests/                      Timestamp and marker regressions
server/
  apps/api/                   FastAPI routes, controllers and configuration
  modules/trading/
    domain/                   Entities, aggregates, strategies and ports
    application/services/     Use cases and asynchronous engine
    infrastructure/           Binance, PostgreSQL and mock adapters
  tests/                      Automated suite and original experiments
docker/init.sql               Schema for a new database
scripts/                      Non-destructive migrations for older installations
docs/                         Academic report and dashboard screenshots
.github/workflows/ci.yml       GitHub Actions tests and frontend build
```

Main stack: **Python 3.11+, FastAPI, Pydantic, asyncio, asyncpg, PostgreSQL 16, React 18, TypeScript, Vite, Tailwind CSS, Lightweight Charts and Recharts**. Resolved dependency versions are recorded in `uv.lock` and `client/package-lock.json`.

## Local development

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 22+ and PostgreSQL. Run from the repository root:

```bash
docker compose up -d postgres
uv sync --frozen
uv run uvicorn apps.api.main:app --app-dir server --reload
```

In a second terminal:

```bash
cd client
npm ci
npm run dev
```

## Tests and continuous integration

```bash
# Domain, strategies, adapters and API regressions; no exchange credentials required
uv run pytest -q

# Frontend timestamp tests and production build
cd client
npm ci
npm test
npm run build
```

To include the PostgreSQL integration regression, start the database and set `TEST_DATABASE_URL`:

```powershell
# PowerShell
$env:TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/trading"
uv run pytest -q
```

```bash
# macOS / Linux
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trading uv run pytest -q
```

The database test creates and removes its own isolated schema. It checks UTC storage, recent candle selection, legacy migration, saved strategy parameters, positions, cash remainders and completed trades after reload. Other regressions cover strategy form metadata and engine shutdown.

GitHub Actions was added during the post-submission cleanup. It runs the backend on Python 3.11 and 3.13 with different time zones and a PostgreSQL service, plus frontend tests and the production build on Node.js 22.

Pytest selects the automated suite explicitly. Original integration and experiment scripts remain in `server/tests`, outside that suite; some require external services or can place Testnet orders.

### Manual verification

The dashboard was reviewed in Chromium at desktop and 390 px mobile widths. A portfolio created through the UI ran the random *Mock Strategy* on BTC/USDT one-minute candles with 30 USDT of Testnet capital. It bought and sold 0.00035 BTC, recorded one completed trade, and retained 29.997578 USDT after reload. Both fills matched the exchange's quantities, prices and UTC timestamps to the millisecond. The engine was then stopped with no open positions.

The same trade displayed identical UTC dates in browsers configured for Europe/Madrid and America/New_York, with BUY/SELL markers rendered on the chart. A separate moving-average backtest completed over 10,000 candles. These checks validate the tested paths, not strategy profitability or production readiness.

## UTC and the original chart issue

The [academic report](docs/memoria.pdf) describes removing trade markers because they appeared on the wrong candles. The cleanup fixes the timestamp path:

- Binance Unix milliseconds become timezone-aware UTC `datetime` values. The API emits ISO 8601 timestamps with an explicit offset.
- PostgreSQL stores instants in `TIMESTAMPTZ` columns. Limited candle queries return the **latest** records in chronological order.
- Charts consume Unix seconds without adding the browser's time zone offset. Clock, tables and chart labels explicitly show UTC.
- Live positions retain the exchange execution time rather than the application server's clock time.
- Each trade marker is placed on the candle containing its execution time. Trades outside the loaded history or inside missing-data gaps are excluded.
- Duplicate candle updates replace the existing candle. Older updates cannot move the current candle backwards; stream updates received while history loads are merged into that history.

Regression cases include summer/winter offsets, the repeated daylight-saving hour, fractional seconds, candle boundaries, calendar months and overlapping trades.

### Upgrading an existing database

New installations need no migration. Back up an existing database and stop the backend before upgrading.

For legacy timezone-naive columns:

```bash
uv run python scripts/migrate_utc.py --source-timezone UTC
```

Use the **original backend's time zone**: usually `UTC` for the original Docker setup, or `Europe/Madrid` if it saved Spanish local wall times. Database-generated `created_at` values default to UTC; use `--created-timezone` if that original database session used another zone. The script preserves rows and skips columns already converted. Mixed-origin or ambiguous daylight-saving timestamps require manual review because a naive timestamp cannot reveal its original offset.

For databases created before strategy parameters were persisted:

```powershell
# PowerShell, with the local Compose database running
Get-Content scripts/migrate_strategy_params.sql | docker compose exec -T postgres psql -U postgres -d trading -v ON_ERROR_STOP=1
```

```bash
# macOS / Linux
docker compose exec -T postgres psql -U postgres -d trading -v ON_ERROR_STOP=1 < scripts/migrate_strategy_params.sql
```

This adds a JSONB column without removing rows. Existing traders keep their previous default settings; parameters that were never saved cannot be recovered. **Do not rerun `docker/init.sql` against an existing database.**

## API overview

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | API process health |
| `PUT` | `/candles/sync` | Synchronize public market data |
| `GET` | `/candles/{symbol}/{interval}` | Read candles; intervals such as `M1`, `H1`, `D1` |
| `WS` | `/live_candles/{symbol}/{interval}` | Live candle stream |
| `POST` | `/api/backtest` | Run a simulation; intervals such as `1m`, `1h`, `1d` |
| `GET` | `/api/portfolio/strategies` | Available strategies and parameters |
| `POST` | `/api/portfolio/create` | Create a portfolio |
| `GET` | `/api/portfolio/trades/{portfolio_id}` | Read completed trades |
| `POST` | `/api/trading/start/{portfolio_id}` | Start Testnet execution |
| `POST` | `/api/trading/stop/{portfolio_id}` | Stop the engine |

Explore request schemas and the remaining endpoints at `/docs` after starting FastAPI.

## Scope and limitations

This is an **educational prototype for local use**, with no authentication or user isolation. It is not ready to manage real funds or expose its trading API to the Internet.

- Backtesting fills at candle close and does not model fees, slippage, liquidity or latency. Portfolio PnL is gross of exchange fees.
- Public market candles and Spot Testnet order prices can differ. Testnet balances and results are test data.
- The order sizing path currently assumes a `0.00001` quantity step. Supporting arbitrary pairs requires exchange-specific lot-size and notional filters, partial-fill handling and reconciliation.
- Automatic stream recovery, coordination across processes and atomic reconciliation of exchange fills with database writes remain future work.
- Monthly charts use calendar boundaries, but the engine's candle buffer approximates a month as 30 days. Use fixed-duration intervals for engine execution.
- The candlestick-pattern strategy remains outside the dashboard options, as in the original submission.
- Binance access depends on connectivity and regional availability. If synchronization fails, the chart reports it and attempts to use stored history.

The academic report is preserved as submitted in February 2026. Its discussion of bugs describes that version; this README documents the subsequent fixes.

## Author

[Rafael Ayudarte](https://github.com/rafaayud) · Universidad de las Hespérides.
