from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from src.trading.application.services.trading_engine import TradingEngine
from src.trading.infrastructure.binance_adapter import BinanceAdapter
from src.trading.infrastructure.postgre_adapter import PostgresAdapter
from src.trading.domain.value_objects import Symbol, Interval
from src.trading.application.services.ingestion_service import DataIngestionService
from src.trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter
from pydantic import BaseModel
from typing import Union

app = FastAPI()

URL_DB = "postgresql://postgres:1234@localhost:5432/postgres"
@app.get("/candles/{symbol}/{interval}")
async def get_candles(
    symbol: str,              # Path param (obligatorio) → viene de la URL
    interval: str,            # Path param (obligatorio) → viene de la URL
    limit: int = 100          # Query param (opcional)   → ?limit=500
) -> dict:
    # Conviertes a tus tipos DENTRO de la función
     async with PostgresAdapter(URL_DB) as storage:
        candles = await storage.get_candles(
            Symbol(symbol),
            Interval[interval],  # ✅ Convierte string → Interval
            limit
        )
        return {"candles": candles}

class SyncRequest(BaseModel):
    symbols: list[str] = ["BTCUSDT"]
    intervals: list[str] = ["H1"]

@app.put("/candles/sync")
async def sync_candles(request: SyncRequest) -> dict:
    """
    Sync candles from Binance to PostgreSQL.
    
    Request body:
    {
        "symbols": ["BTCUSDT", "ETHUSDT"],  # Optional, default: ["BTCUSDT"]
        "intervals": ["H1", "M15"]           # Optional, default: ["H1"]
    }
    
    Intervals: "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MO1"
    """
    async with DataIngestionService(PostgresAdapter(URL_DB), BinanceAdapter()) as service:
        await service.sync_all([Symbol(s) for s in request.symbols], [Interval[i] for i in request.intervals])
    return {"status": "synced"}


@app.websocket("/candles_live/{symbol}/{interval}")
async def stream_candles(websocket: WebSocket, symbol: str, interval: str) -> None:
    await websocket.accept()  # Acepta la conexión
    
    try:
        async with BinanceStreamAdapter() as stream:
            async for candle in stream.stream_candle(Symbol(symbol), Interval[interval]):
                 
                await websocket.send_json({
             "symbol": symbol,
            "interval": interval,
             "candle": {
            "open_time": candle.open_time.timestamp.isoformat(),
            "open": float(candle.ohlcv.open),
            "high": float(candle.ohlcv.high),
            "low": float(candle.ohlcv.low),
            "close": float(candle.ohlcv.close),
            "volume": float(candle.ohlcv.volume),
        }
    })

    except WebSocketDisconnect:
        print(f"Cliente desconectado de {symbol}/{interval}")
