from fastapi import APIRouter, Depends, Query
from apps.api.controllers.trading_controller import TradingController
from apps.api.service_factory import ServiceFactory
from apps.api.dependencies import get_service_factory

router = APIRouter(tags=["trading"])
controller = TradingController()

@router.post("/start/{portfolio_id}")
async def start_trading(
    portfolio_id: str,
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Start trading for a portfolio"""
    return await controller.start_trading(portfolio_id, service_factory)

@router.post("/stop/{portfolio_id}")
async def stop_trading(
    portfolio_id: str,
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Stop trading for a portfolio"""
    return await controller.stop_trading(portfolio_id, service_factory)

@router.get("/status/{portfolio_id}")
async def get_trading_status(
    portfolio_id: str,
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Get trading status for a portfolio"""
    return await controller.get_trading_status(portfolio_id, service_factory)

@router.get("/portfolio/{portfolio_id}")
async def get_active_portfolio(
    portfolio_id: str,
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Get active portfolio with their details"""
    return await controller.get_active_strategies(portfolio_id, service_factory)

@router.get("/trades/{portfolio_id}")
async def get_trades(
    portfolio_id: str,
    trader_id: str = Query(default=None, description="Optional trader ID to filter trades"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of trades to return"),
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Get trades for a portfolio, optionally filtered by trader"""
    return await controller.get_trades(portfolio_id, trader_id, limit, service_factory)

@router.get("/chart/{portfolio_id}/{trader_id}")
async def get_chart_data(
    portfolio_id: str,
    trader_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of candles to return"),
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Get chart data (candles) for a specific trader's symbol and interval with trade markers"""
    return await controller.get_chart_data(portfolio_id, trader_id, limit, service_factory)
