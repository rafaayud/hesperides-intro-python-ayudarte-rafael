"""Pydantic schemas for trading endpoints"""
from pydantic import BaseModel
from typing import Optional


class StrategyParams(BaseModel):
    """Strategy-specific parameters"""
    # MockStrategy
    min_candles: Optional[int] = None
    execution_mode: Optional[str] = None  # "ON_CLOSE" or "ON_TICK"
    
    # MeanCross
    slow_period: Optional[int] = None
    fast_period: Optional[int] = None
    
    # Momentum
    reference_period: Optional[int] = None
    threshold: Optional[float] = None
    
    # CandlePatternStrategy
    patterns: Optional[list] = None


class TraderConfig(BaseModel):
    """Configuration for a single trader"""
    symbol: str
    interval: str
    strategy: str = "mock_strategy"  # "mock_strategy", "mean_cross", "momentum", "candle_pattern"
    strategy_params: Optional[StrategyParams] = None

class AdapterConfig(BaseModel):
    """Configuration for adapters used by the trading engine"""
    exchange: Optional[str] = None
    stream: Optional[str] = None
    order: Optional[str] = None
    portfolio_storage: Optional[str] = None

class CreateTradingRequest(BaseModel):
    """Request to create a trading portfolio"""
    name: str
    portfolio_id: str
    traders: list[TraderConfig]  # Lista de traders con su configuración
    capital: float
    adapters: Optional[AdapterConfig] = None

