# Diagramas UML del Backend

Este directorio contiene los diagramas UML que representan la arquitectura y el diseño del sistema de trading.

## Diagramas Disponibles

### 1. Diagrama de Clases del Dominio (`01_diagrama_clases_dominio.puml`)
Muestra la estructura de clases del dominio, incluyendo:
- **Value Objects**: Symbol, Interval, Price, Quantity, Timestamp, Signal, TradeStatus, Candle_static, PnL
- **Entities**: Trade, Position, Candle, Order, OrderResponse
- **Aggregates**: Portfolio, Trader, CandleBuffer, BacktestResult
- **Strategies**: Strategy (abstracta), MeanCross, Momentum, MeanCrossTakeProfit, MockStrategy

**Relaciones principales:**
- Portfolio contiene múltiples Traders
- Trader usa una Strategy y contiene un CandleBuffer
- Portfolio gestiona Positions y Trades
- Las estrategias heredan de Strategy

### 2. Diagrama de Componentes (`02_diagrama_componentes.puml`)
Representa la arquitectura hexagonal del sistema:
- **API Layer**: FastAPI, Controllers
- **Application Services**: TradingEngine, PortfolioManager, BacktestService, IngestionService, StrategyFactory
- **Domain Layer**: Aggregates, Strategies, Ports (interfaces)
- **Infrastructure Layer**: Adapters para Binance y PostgreSQL
- **External Systems**: Binance Exchange, PostgreSQL

**Arquitectura Hexagonal:**
- Los Ports definen las interfaces (ExchangePort, StreamPort, OrderPort, StoragePort, PortfolioStoragePort)
- Los Adapters implementan los Ports
- La aplicación depende de los Ports, no de los Adapters concretos

### 3. Diagrama de Secuencia - Trading en Tiempo Real (`03_diagrama_secuencia_trading.puml`)
Muestra el flujo completo de trading en tiempo real:
1. **Inicialización**: Restauración del estado del portfolio, warm-up de traders
2. **Loop de Trading**:
   - Recepción de velas del WebSocket
   - Actualización del CandleBuffer
   - Generación de señales por la Strategy
   - Ejecución de órdenes en Binance
   - Actualización del Portfolio

### 4. Diagrama de Secuencia - Backtest (`04_diagrama_secuencia_backtest.puml`)
Muestra el flujo de ejecución de un backtest:
1. **Sincronización de Datos**: Descarga de velas históricas de Binance y guardado en PostgreSQL
2. **Ejecución del Backtest**: 
   - Obtención de velas de la base de datos
   - Creación de la estrategia
   - Simulación de trading sobre las velas históricas
   - Cálculo de métricas (PnL, win rate, etc.)

## Cómo Visualizar los Diagramas

### Opción 1: PlantUML Online
1. Copia el contenido de cualquier archivo `.puml`
2. Visita https://www.plantuml.com/plantuml/uml/
3. Pega el contenido y visualiza

### Opción 2: VS Code Extension
1. Instala la extensión "PlantUML" en VS Code
2. Abre cualquier archivo `.puml`
3. Presiona `Alt+D` para previsualizar

### Opción 3: PlantUML CLI
```bash
# Instalar PlantUML (requiere Java)
# Descargar desde: https://plantuml.com/download

# Generar imagen PNG
java -jar plantuml.jar docs/uml/01_diagrama_clases_dominio.puml

# Generar SVG
java -jar plantuml.jar -tsvg docs/uml/01_diagrama_clases_dominio.puml
```

## Estructura del Sistema

```
Backend
├── Domain Layer (Core Business Logic)
│   ├── Aggregates (Portfolio, Trader, CandleBuffer)
│   ├── Entities (Trade, Position, Order)
│   ├── Value Objects (Symbol, Price, Signal, etc.)
│   └── Strategies (MeanCross, Momentum, etc.)
│
├── Application Layer (Use Cases)
│   ├── TradingEngine (Orchestrates real-time trading)
│   ├── PortfolioManager (Manages portfolios)
│   ├── BacktestService (Runs backtests)
│   └── IngestionService (Syncs data from exchange)
│
├── Infrastructure Layer (Adapters)
│   ├── BinanceExchangeAdapter (REST API)
│   ├── BinanceStreamAdapter (WebSocket)
│   ├── BinanceOrderAdapter (Order execution)
│   ├── PostgresStorageAdapter (Candles storage)
│   └── PostgresPortfolioAdapter (Portfolio storage)
│
└── API Layer (HTTP Interface)
    ├── FastAPI (Web framework)
    ├── Controllers (Request handlers)
    └── Routers (API endpoints)
```

## Notas de Diseño

- **Arquitectura Hexagonal**: El dominio está aislado de la infraestructura mediante Ports (interfaces)
- **Aggregates**: Portfolio es el aggregate root que gestiona Traders, Positions y Trades
- **Value Objects**: Inmutables, validan invariantes del dominio
- **Strategies**: Patrón Strategy para diferentes algoritmos de trading
- **3-Queue Pipeline**: TradingEngine usa 3 colas para procesar velas, órdenes y respuestas de forma asíncrona

