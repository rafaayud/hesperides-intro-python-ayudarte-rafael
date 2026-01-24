from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from apps.api.controllers.trading_controller import TradingController
from apps.api.service_factory import ServiceFactory
from apps.api.dependencies import get_service_factory

router = APIRouter(prefix="/trading", tags=["trading"])
controller = TradingController()


class CreateTradingRequest(BaseModel):
    symbol: str = ["BTCUSDT"]
    intervals: str = ["H1"]
    strategy: str = "MockStrategy"
    min_candles: int = 10
    capital: float = 1000.0



@router.post("/create")
async def create_trading(request: CreateTradingRequest, service_factory: ServiceFactory = Depends(get_service_factory)) -> dict:
    """Create a new trading strategy or use an existing one"""
    return await controller.create_trading(request.model_dump(), service_factory)
