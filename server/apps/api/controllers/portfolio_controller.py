import logging
from decimal import Decimal
from fastapi import HTTPException
from modules.trading.domain.value_objects import Symbol, Interval
from modules.trading.domain.aggregates import Portfolio, Trader
from modules.trading.application.services.strategy_factory import StrategyFactory
from apps.api.service_factory import ServiceFactory
from apps.api.schemas.trading import CreateTradingRequest

logger = logging.getLogger(__name__)


class PortfolioController:
    """Controller for portfolio management operations"""
    
    async def get_strategies(self) -> dict:
        """
        Get all available trading strategies with their metadata.
        
        Returns:
            dict: List of strategies with name, description, and parameter info
        """
        
        
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
        
        return {
            "strategies": [
                {
                    "id": strategy,  
                    "name": strategy,
                    "display_name": strategy_metadata.get(strategy, {}).get("display_name", strategy),
                    "description": strategy_metadata.get(strategy, {}).get("description", "")
                }
                for strategy in strategies
            ]
        }
    
    async def get_strategy_params(self, strategy_name: str) -> dict:
        """
        Get parameter schema for a specific strategy.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            dict: Parameter schema for the strategy
        """
        
        
        param_schemas = {
            "mock_strategy": {
                "common_params": [
                    {"name": "min_candles", "type": "number", "default": 10, "description": "Minimum number of candles required before trading"},
                    {"name": "execution_mode", "type": "string", "default": "ON_CLOSE", "description": "When to execute trades", "enum": ["ON_CLOSE", "ON_TICK"]}
                ],
                "specific_params": []
            },
            "mean_cross": {
                "common_params": [
                    {"name": "execution_mode", "type": "string", "default": "ON_CLOSE", "description": "When to execute trades", "enum": ["ON_CLOSE", "ON_TICK"]}
                ],
                "specific_params": [
                    {"name": "slow_period", "type": "number", "default": 50, "description": "Period for slow moving average"},
                    {"name": "fast_period", "type": "number", "default": 10, "description": "Period for fast moving average"}
                ]
            },
            "momentum": {
                "common_params": [],
                "specific_params": [
                    {"name": "reference_period", "type": "number", "default": 14, "description": "Number of candles to look back for momentum calculation"},
                    {"name": "threshold", "type": "number", "default": 0.02, "description": "Minimum percentage change to trigger a signal (e.g., 0.02 = 2%)"}
                ]
            },
            "candle_pattern": {
                "common_params": [],
                "specific_params": [
                    {"name": "pattern_type", "type": "string", "default": "doji", "description": "Type of candlestick pattern to detect", "enum": ["doji", "hammer", "engulfing"]},
                    {"name": "confidence", "type": "number", "default": 0.7, "description": "Confidence threshold for pattern detection (0-1)"}
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
    
    async def create_portfolio(
        self, 
        request: CreateTradingRequest, 
        service_factory: ServiceFactory
    ) -> dict:
        """
        Create a new trading portfolio.
        
        Args:
            request: Request with portfolio configuration
            service_factory: Factory to create services
            
        Returns:
            dict: Portfolio information
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
                traders=traders)
            
            # 3. Create portfolio manager with specified adapters
            adapter_config = request.adapters if request.adapters else None
            
            portfolio_manager = service_factory.create_portfolio_manager(
                portfolio_storage=adapter_config.portfolio_storage if adapter_config else None
            )
            
            # 4. Initialize portfolio in manager
            portfolio_manager.initialize_portfolio(portfolio)
            
            # 5. Connect portfolio manager (connects storage)
            await portfolio_manager.connect()
            
            # 6. Restore state (saves if new, restores if exists)
            await portfolio_manager.restore_state()
            
            # 7. Disconnect (will be reconnected when trading starts)
            await portfolio_manager.disconnect()
            
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
            logger.error(f"Error creating portfolio: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to create portfolio: {str(e)}"
            )


    async def get_portfolio(self, portfolio_id: str, service_factory: ServiceFactory) -> dict:
        """
        Get a portfolio by its ID.
        
        Args:
            portfolio_id: ID of the portfolio to get
            
        Returns:
            dict: Portfolio information
        """
        try:
            # 1. Get portfolio manager
            portfolio_manager = service_factory.create_portfolio_manager()
            
            # 2. Load portfolio from database
            portfolio = await portfolio_manager.load_portfolio(portfolio_id)
            
            # 3. Disconnect portfolio manager
            await portfolio_manager.disconnect()
            
            return {
                "status": "success",
                "portfolio_id": portfolio.id,
                "portfolio_name": portfolio.name,
                "traders_count": len(portfolio.traders),
                "capital": float(portfolio.initial_capital)
            }

        except Exception as e:
            logger.error(f"Error getting portfolio: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to get portfolio: {str(e)}"
            )
    
    async def list_portfolios(self, service_factory: ServiceFactory) -> dict:
        """
        List all portfolios.
        
        Args:
            service_factory: Factory to create services
            
        Returns:
            dict: List of portfolios
        """
        try:
            # 1. Get portfolio manager
            portfolio_manager = service_factory.create_portfolio_manager()
            await portfolio_manager.connect()
            
            try:
                # 2. List portfolios from database
                portfolios = await portfolio_manager._storage.list_portfolios()
                
                return {
                    "status": "success",
                    "portfolios": portfolios
                }
            finally:
                await portfolio_manager.disconnect()
                
        except Exception as e:
            logger.error(f"Error listing portfolios: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to list portfolios: {str(e)}"
            )