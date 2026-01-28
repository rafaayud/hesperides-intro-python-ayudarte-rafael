from fastapi import APIRouter, Depends
from apps.api.controllers.portfolio_controller import PortfolioController
from apps.api.service_factory import ServiceFactory
from apps.api.dependencies import get_service_factory
from apps.api.schemas.trading import CreateTradingRequest

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
