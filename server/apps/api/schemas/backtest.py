from pydantic import BaseModel
from apps.api.schemas.trading import StrategyParams
from typing import Optional

class BacktestRequest(BaseModel):
    symbol: str
    interval: str
    strategy: str = "mock_strategy"
    strategy_params: Optional[StrategyParams] = None
    initial_capital: float = 10000