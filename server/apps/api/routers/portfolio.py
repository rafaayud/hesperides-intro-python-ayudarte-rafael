from fastapi import APIRouter, Depends
from apps.api.controllers.portfolio_controller import PortfolioController
from apps.api.service_factory import ServiceFactory
from apps.api.dependencies import get_service_factory
from apps.api.dependencies import get_trading_state
from apps.api.trading_state import TradingStateManager
from apps.api.schemas.trading import CreateTradingRequest
from typing import Optional

router = APIRouter(tags=["portfolio"])
controller = PortfolioController()

@router.get("/strategies")
async def get_strategies() -> dict:
    """Get all available trading strategies"""
    return await controller.get_strategies()

@router.get("/strategies/{strategy_name}/params")
async def get_strategy_params(strategy_name: str) -> dict:
    """Get parameters schema for a specific strategy"""
    return await controller.get_strategy_params(strategy_name)

@router.post("/create")
async def create_portfolio(
    request: CreateTradingRequest, 
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Create a new trading portfolio"""
    return await controller.create_portfolio(request, service_factory)

@router.get("/list")
async def list_portfolios(service_factory: ServiceFactory = Depends(get_service_factory)) -> dict:
    """List all portfolios"""
    return await controller.list_portfolios(service_factory)

@router.get("/{portfolio_id}")
async def get_portfolio(portfolio_id: str, service_factory: ServiceFactory = Depends(get_service_factory)) -> dict:
    """Get a portfolio by its ID"""
    return await controller.get_portfolio(portfolio_id, service_factory)

@router.get("/active/{portfolio_id}")
async def get_active_portfolio(portfolio_id: str, service_factory: ServiceFactory = Depends(get_service_factory), trading_state: TradingStateManager = Depends(get_trading_state)) -> dict:
    """Get active portfolio with their details"""
    return await controller.get_active_portfolio(portfolio_id, service_factory, trading_state)

@router.get("/traders/{portfolio_id}")
async def get_traders(portfolio_id: str, service_factory: ServiceFactory = Depends(get_service_factory)) -> dict:
    """Get all traders for a portfolio"""
    return await controller.get_traders(portfolio_id, service_factory)

@router.get("/trades/{portfolio_id}")
async def get_trades(portfolio_id: str, trader_id: Optional[str] = None, limit: int = 100, service_factory: ServiceFactory = Depends(get_service_factory), trading_state: TradingStateManager = Depends(get_trading_state)) -> dict:
    """Get trades for a portfolio, optionally filtered by trader"""
    return await controller.get_trades(portfolio_id, trader_id, limit, service_factory)

@router.get("/chart/{portfolio_id}/{trader_id}")
async def get_chart_data(portfolio_id: str, trader_id: str, limit: int = 100, service_factory: ServiceFactory = Depends(get_service_factory), trading_state: TradingStateManager = Depends(get_trading_state)) -> dict:
    """Get chart data (candles) for a specific trader's symbol and interval"""
    return await controller.get_chart_data(portfolio_id, trader_id, limit, service_factory)

@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: str, service_factory: ServiceFactory = Depends(get_service_factory), trading_state: TradingStateManager = Depends(get_trading_state)) -> dict:
    """Delete a portfolio by its ID"""
    return await controller.delete_portfolio(portfolio_id, service_factory, trading_state)

@router.get("/stats/global")
async def get_global_stats(service_factory: ServiceFactory = Depends(get_service_factory), trading_state: TradingStateManager = Depends(get_trading_state)) -> dict:
    """Get global statistics across all portfolios"""
    return await controller.get_global_stats(service_factory, trading_state)

@router.get("/positions/open")
async def get_open_positions(service_factory: ServiceFactory = Depends(get_service_factory), trading_state: TradingStateManager = Depends(get_trading_state)) -> dict:
    """Get all open positions across all portfolios"""
    return await controller.get_open_positions(service_factory, trading_state)

@router.get("/positions/{portfolio_id}")
async def get_positions(portfolio_id: str, service_factory: ServiceFactory = Depends(get_service_factory)) -> dict:
    """Get positions for a portfolio"""
    return await controller.get_positions(portfolio_id, service_factory)