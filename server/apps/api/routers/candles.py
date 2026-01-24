from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from apps.api.controllers.candle_controller import CandleController
from apps.api.service_factory import ServiceFactory
from apps.api.dependencies import get_service_factory

router = APIRouter(prefix="/candles", tags=["candles"])
controller = CandleController()


class SyncRequest(BaseModel):
    symbols: list[str] = ["BTCUSDT"]
    intervals: list[str] = ["H1"]
    exchange: str | None = None
    storage: str | None = None


@router.get("/{symbol}/{interval}")
async def get_candles(
    symbol: str, 
    interval: str, 
    limit: int = Query(default=100, le=10000, ge=1), 
    storage: str | None = Query(default=None),
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Get candles for a given symbol and interval"""
    return await controller.get_candles(symbol, interval, limit, storage, service_factory)


@router.put("/sync")
async def sync_candles(
    request_body: SyncRequest,
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Sync candles from exchange to storage"""
    return await controller.sync_candles(request_body.model_dump(), service_factory)




