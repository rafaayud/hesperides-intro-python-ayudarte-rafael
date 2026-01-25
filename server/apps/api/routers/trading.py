from fastapi import APIRouter, Query, Depends
from apps.api.controllers.trading_controller import TradingController
from apps.api.service_factory import ServiceFactory
from apps.api.dependencies import get_service_factory
from apps.api.schemas.trading import CreateTradingRequest

router = APIRouter(tags=["trading"])
controller = TradingController()

@router.get("/strategies")
async def get_strategies() -> dict:
    """Get all available trading strategies"""
    return await controller.get_strategies()

@router.get("/strategies/{strategy_name}/params")
async def get_strategy_params(strategy_name: str) -> dict:
    """Get parameters schema for a specific strategy"""
    return await controller.get_strategy_params(strategy_name)

@router.post("/create")
async def create_trading(
    request: CreateTradingRequest, 
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Create a new trading portfolio and initialize the trading engine"""
    return await controller.create_trading(request, service_factory)
