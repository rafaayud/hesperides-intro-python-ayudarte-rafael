from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..trading.domain.ports import StoragePort
from ..trading.domain.value_objects import Symbol, Interval

from .config import Settings, get_settings
from .dependencies import AdapterRegistry, setup_registry
from .service_factory import ServiceFactory

logger = logging.getLogger(__name__)


# ============ LIFESPAN (startup/shutdown) ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    setup_registry(settings)
    app.state.settings = settings
    app.state.services = ServiceFactory(AdapterRegistry, settings)
    print("✅ Registry initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ DEPENDENCIES ============
async def get_storage(
    storage: str = Query(default=None, description="Storage backend: postgres"),
    settings: Settings = Depends(get_settings)
) -> StoragePort:
    """Dependency that returns storage with lifecycle managed"""
    try:
        storage_name = storage or settings.default_storage
        adapter = AdapterRegistry.get_storage(storage_name, database_url=settings.database_url)
        async with adapter:
            yield adapter
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Storage backend '{storage_name}' not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing storage: {str(e)}")


def get_service_factory() -> ServiceFactory:
    """Access the ServiceFactory from app.state"""
    from fastapi import Request
    def _get(request: Request) -> ServiceFactory:
        return request.app.state.services
    return Depends(_get)


# ============ SCHEMAS ============
class SyncRequest(BaseModel):
    symbols: list[str] = ["BTCUSDT"]
    intervals: list[str] = ["H1"]
    exchange: str | None = None  


class CandleResponse(BaseModel):
    open_time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


# ============ HELPERS ============
def serialize_candle(candle) -> dict:
    return {
        "open_time": candle.timestamp.timestamp.isoformat(),
        "open": float(candle.open.value),
        "high": float(candle.high.value),
        "low": float(candle.low.value),
        "close": float(candle.close.value),
        "volume": float(candle.volume.value),
    }


# ============ ENDPOINTS ============
@app.get("/candles/{symbol}/{interval}")
async def get_candles(
    symbol: str,
    interval: str,
    limit: int = Query(default=100, le=10000, ge=1),
    storage: StoragePort = Depends(get_storage)
) -> dict:
    """Obtiene velas históricas desde storage"""
    logger.info(f"GET /candles/{symbol}/{interval}?limit={limit}")
    
    try:
        interval_upper = interval.upper()
        logger.info(f"Attempting to parse interval: '{interval}' -> '{interval_upper}'")
        interval_enum = Interval[interval_upper]
        logger.info(f"Parsed interval: {interval_enum}")
    except KeyError as e:
        valid_intervals = [i.name for i in Interval]
        logger.error(f"Invalid interval: '{interval}' (upper: '{interval.upper()}'). Valid: {valid_intervals}")
        raise HTTPException(
            status_code=422, 
            detail=f"Invalid interval: '{interval}'. Valid intervals: {valid_intervals}"
        )
    
    try:
        candles = await storage.get_candles(
            Symbol(symbol),
            interval_enum,
            limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching candles: {str(e)}")
    
    return {"candles": [serialize_candle(c) for c in candles]}


@app.put("/candles/sync")
async def sync_candles(
    request: SyncRequest,
    settings: Settings = Depends(get_settings)) -> dict:
    """Sincroniza velas desde exchange a storage"""
    services = ServiceFactory(AdapterRegistry, settings)
    
    async with services.create_ingestion_service(exchange=request.exchange) as service:
        await service.sync_all(
            [Symbol(s) for s in request.symbols],
            [Interval[i] for i in request.intervals]
        )
    
    return {
        "status": "synced",
        "symbols": request.symbols,
        "intervals": request.intervals
    }


@app.websocket("/candles_live/{symbol}/{interval}")
async def stream_candles(
    websocket: WebSocket, 
    symbol: str, 
    interval: str,
    exchange: str = "binance"  # Query param para WebSocket
):
    """Stream de velas en tiempo real via WebSocket"""
    await websocket.accept()
    
    try:
        stream = AdapterRegistry.get_stream(exchange)
        async with stream:
            async for candle in stream.stream_candle(Symbol(symbol), Interval[interval]):
                await websocket.send_json({
                    "symbol": symbol,
                    "interval": interval,
                    "candle": {
                        "open_time": candle.open_time.timestamp.isoformat(),
                        "open": float(candle.ohlcv.open.value),
                        "high": float(candle.ohlcv.high.value),
                        "low": float(candle.ohlcv.low.value),
                        "close": float(candle.ohlcv.close.value),
                        "volume": float(candle.ohlcv.volume.value),
                        "is_closed": candle.is_closed
                    }
                })
    except WebSocketDisconnect:
        print(f"Cliente desconectado de {symbol}/{interval}")
    except Exception as e:
        print(f"Error en stream: {e}")
        await websocket.close(code=1011)


# ============ HEALTH & INFO ============
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/info/adapters")
async def list_adapters():
    """Lista los adaptadores registrados"""
    return {
        "exchanges": list(AdapterRegistry._exchanges.keys()),
        "storages": list(AdapterRegistry._storages.keys()),
        "streams": list(AdapterRegistry._streams.keys()),
    }
