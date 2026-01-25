import logging
from decimal import Decimal
from fastapi import HTTPException
from modules.trading.domain.value_objects import Symbol, Interval
from modules.trading.domain.aggregates import Portfolio, Trader
from modules.trading.application.services.strategy_factory import StrategyFactory
from apps.api.service_factory import ServiceFactory
from apps.api.schemas.trading import CreateTradingRequest

logger = logging.getLogger(__name__)


class TradingController:
    """Controller for trading operations"""
    
    async def get_strategies(self) -> dict:
        """
        Get all available trading strategies with their metadata.
        
        Returns:
            dict: List of strategies with name, description, and parameter info
        """
        from modules.trading.application.services.strategy_factory import StrategyFactory
        
        strategies = StrategyFactory.get_all_strategies()
        
        # Strategy metadata for frontend
        strategy_metadata = {
            "mock_strategy": {
                "name": "Mock Strategy",
                "description": "Random strategy for testing purposes",
                "display_name": "Mock Strategy"
            },
            "mean_cross": {
                "name": "mean_cross",
                "description": "Moving Average Crossover: Buy when fast MA crosses above slow MA",
                "display_name": "Moving Average Cross"
            },
            "momentum": {
                "name": "momentum",
                "description": "Momentum strategy based on price change percentage",
                "display_name": "Momentum"
            },
            "candle_pattern": {
                "name": "candle_pattern",
                "description": "Strategy based on candlestick pattern detection",
                "display_name": "Candle Pattern"
            }
        }
        
        result = []
        for strategy_name in strategies:
            metadata = strategy_metadata.get(strategy_name, {
                "name": strategy_name,
                "description": "",
                "display_name": strategy_name.replace("_", " ").title()
            })
            result.append({
                "id": strategy_name,
                **metadata
            })
        
        return {
            "strategies": result
        }
    
    async def get_strategy_params(self, strategy_name: str) -> dict:
        """
        Get parameter schema for a specific strategy.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            dict: Parameter schema with field definitions for the frontend
        """
        # Parameter schemas for each strategy
        param_schemas = {
            "mock_strategy": {
                "common_params": [
                    {
                        "name": "min_candles",
                        "type": "number",
                        "label": "Minimum Candles",
                        "description": "Minimum number of candles required before trading",
                        "default": 10,
                        "required": False,
                        "min": 1
                    },
                    {
                        "name": "execution_mode",
                        "type": "select",
                        "label": "Execution Mode",
                        "description": "When to execute trades",
                        "options": [
                            {"value": "ON_CLOSE", "label": "On Candle Close"},
                            {"value": "ON_TICK", "label": "On Every Tick"}
                        ],
                        "default": "ON_CLOSE",
                        "required": False
                    }
                ],
                "specific_params": []
            },
            "mean_cross": {
                "common_params": [
                    {
                        "name": "execution_mode",
                        "type": "select",
                        "label": "Execution Mode",
                        "description": "When to execute trades",
                        "options": [
                            {"value": "ON_CLOSE", "label": "On Candle Close"},
                            {"value": "ON_TICK", "label": "On Every Tick"}
                        ],
                        "default": "ON_CLOSE",
                        "required": False
                    }
                ],
                "specific_params": [
                    {
                        "name": "slow_period",
                        "type": "number",
                        "label": "Slow Period",
                        "description": "Period for slow moving average",
                        "default": 50,
                        "required": False,
                        "min": 1
                    },
                    {
                        "name": "fast_period",
                        "type": "number",
                        "label": "Fast Period",
                        "description": "Period for fast moving average",
                        "default": 10,
                        "required": False,
                        "min": 1
                    }
                ]
            },
            "momentum": {
                "common_params": [
                    {
                        "name": "min_candles",
                        "type": "number",
                        "label": "Minimum Candles",
                        "description": "Minimum number of candles required before trading",
                        "default": 10,
                        "required": False,
                        "min": 1
                    },
                    {
                        "name": "execution_mode",
                        "type": "select",
                        "label": "Execution Mode",
                        "description": "When to execute trades",
                        "options": [
                            {"value": "ON_CLOSE", "label": "On Candle Close"},
                            {"value": "ON_TICK", "label": "On Every Tick"}
                        ],
                        "default": "ON_CLOSE",
                        "required": False
                    }
                ],
                "specific_params": [
                    {
                        "name": "reference_period",
                        "type": "number",
                        "label": "Reference Period",
                        "description": "Number of candles to look back for momentum calculation",
                        "default": 14,
                        "required": False,
                        "min": 1
                    },
                    {
                        "name": "threshold",
                        "type": "number",
                        "label": "Threshold",
                        "description": "Minimum percentage change to trigger a signal (e.g., 0.02 = 2%)",
                        "default": 0.02,
                        "required": False,
                        "min": 0,
                        "step": 0.01
                    }
                ]
            },
            "candle_pattern": {
                "common_params": [],
                "specific_params": [
                    {
                        "name": "patterns",
                        "type": "array",
                        "label": "Patterns",
                        "description": "List of candlestick patterns to detect (uses defaults if not specified)",
                        "required": False
                    }
                ]
            }
        }
        
        strategy_lower = strategy_name.lower()
        
        if strategy_lower not in param_schemas:
            from fastapi import HTTPException
            from modules.trading.application.services.strategy_factory import StrategyFactory
            available = ", ".join(StrategyFactory.get_all_strategies())
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found. Available strategies: {available}"
            )
        
        schema = param_schemas[strategy_lower]
        
        return {
            "strategy_name": strategy_lower,
            "parameters": {
                "common": schema["common_params"],
                "specific": schema["specific_params"],
                "all": schema["common_params"] + schema["specific_params"]
            }
        }
    
    async def create_trading(
        self, 
        request: CreateTradingRequest, 
        service_factory: ServiceFactory
    ) -> dict:
        """
        Create a trading portfolio and initialize the trading engine.
        
        Args:
            request: Request with portfolio configuration
            service_factory: Factory to create services
            
        Returns:
            dict: Portfolio information and engine status
        """
        try:
            # 1. Create traders from request
            traders = []
            for trader_config in request.traders:
                # Validate symbol and interval
                try:
                    symbol = Symbol(trader_config.symbol)
                    # Try to convert interval - accept both enum name (H1) and value (1h)
                    interval_str = trader_config.interval.upper()
                    try:
                        # First try as enum name (H1, M1, etc.)
                        interval = Interval[interval_str]
                    except KeyError:
                        # If not found, try as enum value (1h, 1m, etc.)
                        interval = Interval(trader_config.interval)
                except (ValueError, KeyError) as e:
                    valid_intervals = [f"{i.name} ({i.value})" for i in Interval]
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid interval: '{trader_config.interval}'. Valid intervals: {', '.join(valid_intervals)}"
                    )
                
                # Create strategy using factory (factory handles all parameter mapping)
                try:
                    strategy = StrategyFactory.create_strategy(
                        strategy_name=trader_config.strategy,
                        strategy_params=trader_config.strategy_params
                    )
                except (KeyError, ValueError, TypeError) as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid strategy or parameters: {e}"
                    )
                
                # Create trader
                trader = Trader(
                    id=f"{request.portfolio_id}_{symbol.symbol}_{interval.value}",
                    strategy=strategy,
                    symbol=symbol,
                    interval=interval
                )
                traders.append(trader)
            
            # 2. Create portfolio
            portfolio = Portfolio(
                id=request.portfolio_id,
                name=request.name,
                initial_capital=Decimal(str(request.capital)),
                traders=traders
            )
            
            # 3. Create trading engine
            engine = service_factory.create_trading_engine()
            
            # 4. Initialize portfolio in engine
            engine.initialize_portfolio(portfolio)
            
            # 5. Save portfolio to database (via startup)
            await engine.startup()
            
            return {
                "status": "success",
                "portfolio_id": portfolio.id,
                "portfolio_name": portfolio.name,
                "traders_count": len(traders),
                "capital": float(portfolio.initial_capital),
                "traders": [
                    {
                        "id": t.id,
                        "symbol": t.symbol.symbol,
                        "interval": t.interval.value,
                        "strategy": t.strategy.name,
                        "min_candles": t.strategy.min_candles_required
                    }
                    for t in traders
                ]
            }
        except Exception as e:
            logger.error(f"Error creating trading portfolio: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to create trading portfolio: {str(e)}"
            )
