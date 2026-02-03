from fastapi import APIRouter, Depends
from apps.api.service_factory import ServiceFactory
from apps.api.schemas.backtest import BacktestRequest
from apps.api.controllers.backtest_controller import BacktestController
from apps.api.dependencies import get_service_factory


router = APIRouter(tags=["backtest"])
backtest_controller = BacktestController()


@router.post("")
async def backtest(
    backtest_request: BacktestRequest, 
    service_factory: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """Backtest a strategy"""
    return await backtest_controller.backtest(backtest_request, service_factory)