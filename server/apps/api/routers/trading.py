from fastapi import APIRouter, Depends, Query
from apps.api.controllers.trading_controller import TradingController
from apps.api.trading_state import TradingStateManager
from apps.api.service_factory import ServiceFactory
from apps.api.dependencies import get_service_factory
from apps.api.dependencies import get_trading_state

router = APIRouter(tags=["trading"])
controller = TradingController()

@router.post("/start/{portfolio_id}")
async def start_trading(
    portfolio_id: str,
    service_factory: ServiceFactory = Depends(get_service_factory),
    trading_state: TradingStateManager = Depends(get_trading_state)
) -> dict:
    """Start trading for a portfolio"""
    return await controller.start_trading(portfolio_id, service_factory, trading_state)

@router.post("/stop/{portfolio_id}")
async def stop_trading(
    portfolio_id: str,
    service_factory: ServiceFactory = Depends(get_service_factory),
    trading_state: TradingStateManager = Depends(get_trading_state)
) -> dict:
    """Stop trading for a portfolio"""
    return await controller.stop_trading(portfolio_id, service_factory, trading_state)

@router.get("/status/{portfolio_id}")
async def get_trading_status(
    portfolio_id: str,
    service_factory: ServiceFactory = Depends(get_service_factory),
    trading_state: TradingStateManager = Depends(get_trading_state)
) -> dict:
    """Get trading status for a portfolio"""
    return await controller.get_trading_status(portfolio_id, service_factory, trading_state)



@router.get("/chart/{portfolio_id}/{trader_id}")
async def get_chart_data(
    portfolio_id: str,
    trader_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of candles to return"),
    service_factory: ServiceFactory = Depends(get_service_factory),
    trading_state: TradingStateManager = Depends(get_trading_state)
) -> dict:
    """Get chart data (candles) for a specific trader's symbol and interval with trade markers"""
    return await controller.get_chart_data(portfolio_id, trader_id, limit, service_factory, trading_state)
