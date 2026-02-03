import logging
from decimal import Decimal
from fastapi import HTTPException
from modules.trading.domain.value_objects import Symbol, Interval
from modules.trading.domain.aggregates import Portfolio, Trader
from modules.trading.application.services.strategy_factory import StrategyFactory
from apps.api.service_factory import ServiceFactory
from apps.api.schemas.trading import CreateTradingRequest
from apps.api.trading_state import TradingStateManager
from typing import Optional

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
            "mean_cross_take_profit": {
                "name": "mean_cross_take_profit",
                "description": "Moving Average Crossover with Take Profit: Buy when fast MA crosses above slow MA, sell on death cross or take profit",
                "display_name": "MA Cross with Take Profit"
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
                    {"name": "execution_mode", "type": "readonly", "default": "ON_CLOSE", "description": "When to execute trades"}
                ],
                "specific_params": [
                    {"name": "slow_period", "type": "number", "default": 50, "description": "Period for slow moving average"},
                    {"name": "fast_period", "type": "number", "default": 10, "description": "Period for fast moving average"}
                ]
            },
            "mean_cross_take_profit": {
                "common_params": [
                    {"name": "execution_mode", "type": "readonly", "default": "ON_CLOSE", "description": "When to execute trades"}
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
                    id=f"{request.portfolio_id}_{symbol.symbol}_{interval.value}_{strategy.name}",
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
            
            # 5. Connect, restore state, and disconnect (will be reconnected when trading starts)
            async with portfolio_manager:
                await portfolio_manager.restore_state()
            
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
            portfolio_manager = service_factory.create_portfolio_manager()
            async with portfolio_manager:
                portfolio = await portfolio_manager.load_portfolio(portfolio_id)
                
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
            portfolio_manager = service_factory.create_portfolio_manager()
            async with portfolio_manager:
                portfolios = await portfolio_manager._storage.list_portfolios()
                
                return {
                    "status": "success",
                    "portfolios": portfolios
                }
                
        except Exception as e:
            logger.error(f"Error listing portfolios: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to list portfolios: {str(e)}"
            )

    async def get_active_portfolio(self, portfolio_id: str, service_factory: ServiceFactory, trading_state: TradingStateManager) -> dict:
        """
        Get active portfolio with their details.
        Returns portfolio from active trading engine if running, otherwise from database.
        """
        try:
            if not await trading_state.is_running(portfolio_id):
                raise HTTPException(
                    status_code=404,
                    detail=f"Portfolio not found: {portfolio_id}"
                )
            
            engine = await trading_state.get_engine(portfolio_id)

            return {
                "portfolio_id": portfolio_id,
                "portfolio_name": engine._portfolio_manager.portfolio.name,
                "portfolio_capital": engine._portfolio_manager.portfolio.initial_capital,
                "portfolio_traders": len(engine._portfolio_manager.portfolio.traders)
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting active portfolio for {portfolio_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get active portfolio: {str(e)}"
            )

    async def get_traders(self, portfolio_id: str, service_factory: Optional[ServiceFactory] = None) -> dict:
        """
        Get all traders for a portfolio.
        """
        try:
            portfolio_manager = service_factory.create_portfolio_manager()
            async with portfolio_manager:
                portfolio = await portfolio_manager.load_portfolio(portfolio_id)
                return {
                    "status": "success",
                    "traders": [trader.to_dict() for trader in portfolio.traders]
                }
        except Exception as e:
            logger.error(f"Error getting traders for {portfolio_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get traders: {str(e)}"
            )

    async def get_trades(self, portfolio_id: str, trader_id: Optional[str] = None, limit: int = 100, service_factory: Optional[ServiceFactory] = None) -> dict:
        """
        Get trades for a portfolio, optionally filtered by trader.
        
        Args:
            portfolio_id: ID of the portfolio
            trader_id: Optional trader ID to filter trades
            limit: Maximum number of trades to return
            service_factory: Factory to create services
            
        Returns:
            dict: List of trades (historical and from active portfolio)
        """
        try:    
            portfolio_manager = service_factory.create_portfolio_manager()
            async with portfolio_manager:
                trades = await portfolio_manager._storage.get_trades(portfolio_id, trader_id, limit)
                
                return {
                    "status": "success",
                    "trades": [trade.to_dict() for trade in trades]
                }

        except Exception as e:
            logger.error(f"Error getting trades for {portfolio_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get trades: {str(e)}"
            )
    
    async def get_chart_data(self, portfolio_id: str, trader_id: str, limit: int = 100, service_factory: Optional[ServiceFactory] = None) -> dict:
        """
        Get chart data (candles) for a specific trader's symbol and interval.
        This allows visualizing where the strategy is operating.
        
        Args:
            portfolio_id: ID of the portfolio
            trader_id: ID of the trader/strategy
            limit: Number of candles to return
            service_factory: Factory to create services
            
        Returns:
            dict: Chart data with candles and trade markers
        """
        pass


    async def delete_portfolio(self, portfolio_id: str, service_factory: ServiceFactory, trading_state: TradingStateManager) -> dict:
        """
        Delete a portfolio by its ID.
        """
        try:
            if trading_state.is_running(portfolio_id):
                await trading_state.shutdown(portfolio_id)

            portfolio_manager = service_factory.create_portfolio_manager()
            async with portfolio_manager:
                await portfolio_manager.delete_portfolio(portfolio_id)
            
            return {"message": "Portfolio deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting portfolio {portfolio_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete portfolio: {str(e)}"
            )
    
    async def get_positions(self, portfolio_id: str, service_factory: ServiceFactory) -> dict:
        """
        Get positions from a portfolio.
        """
        try:
            portfolio_manager = service_factory.create_portfolio_manager()
            async with portfolio_manager:
                positions = await portfolio_manager.get_positions(portfolio_id)
                return {
                    "status": "success",
                    "positions": [position.to_dict() for position in positions]
                }
        except Exception as e:
            logger.error(f"Error getting positions for {portfolio_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get positions: {str(e)}"
            )

    async def get_global_stats(self, service_factory: ServiceFactory, trading_state: TradingStateManager) -> dict:
        """
        Get global statistics across all portfolios.
        """
        try:
            portfolio_manager = service_factory.create_portfolio_manager()
            async with portfolio_manager:
                portfolios = await portfolio_manager._storage.list_portfolios()
                
                total_capital = Decimal("0")
                total_pnl = Decimal("0")
                total_trades = 0
                winning_trades = 0
                running_count = 0
                best_portfolio = {"id": None, "pnl": Decimal("-999999999")}
                worst_portfolio = {"id": None, "pnl": Decimal("999999999")}
                
                for portfolio_info in portfolios:
                    portfolio_id = portfolio_info.get("id")
                    initial_capital = Decimal(str(portfolio_info.get("initial_capital", 0)))
                    total_capital += initial_capital
                    
                    # Check if running
                    if await trading_state.is_running(portfolio_id):
                        running_count += 1
                    
                    # Get trades for PnL calculation
                    try:
                        trades = await portfolio_manager._storage.get_trades(portfolio_id)
                        portfolio_pnl = Decimal("0")
                        for trade in trades:
                            trade_pnl = trade.pnl.value if hasattr(trade, 'pnl') else Decimal("0")
                            portfolio_pnl += trade_pnl
                            total_pnl += trade_pnl
                            total_trades += 1
                            if hasattr(trade, 'winner') and trade.winner:
                                winning_trades += 1
                        
                        if portfolio_pnl > best_portfolio["pnl"]:
                            best_portfolio = {"id": portfolio_id, "pnl": portfolio_pnl}
                        if portfolio_pnl < worst_portfolio["pnl"]:
                            worst_portfolio = {"id": portfolio_id, "pnl": portfolio_pnl}
                    except Exception:
                        pass
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
                
                return {
                    "status": "success",
                    "stats": {
                        "total_portfolios": len(portfolios),
                        "running_portfolios": running_count,
                        "total_capital": float(total_capital),
                        "total_pnl": float(total_pnl),
                        "total_trades": total_trades,
                        "winning_trades": winning_trades,
                        "win_rate": win_rate,
                        "best_portfolio": {
                            "id": best_portfolio["id"],
                            "pnl": float(best_portfolio["pnl"]) if best_portfolio["id"] else None
                        },
                        "worst_portfolio": {
                            "id": worst_portfolio["id"],
                            "pnl": float(worst_portfolio["pnl"]) if worst_portfolio["id"] else None
                        }
                    }
                }
        except Exception as e:
            logger.error(f"Error getting global stats: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get global stats: {str(e)}"
            )

    async def get_open_positions(self, service_factory: ServiceFactory, trading_state: TradingStateManager) -> dict:
        """
        Get all open positions across all portfolios.
        """
        try:
            all_positions = []
            portfolio_manager = service_factory.create_portfolio_manager()
            
            async with portfolio_manager:
                portfolios = await portfolio_manager._storage.list_portfolios()
                
                for portfolio_info in portfolios:
                    portfolio_id = portfolio_info.get("id")
                    try:
                        positions = await portfolio_manager.get_positions(portfolio_id)
                        for position in positions:
                            pos_dict = position.to_dict()
                            pos_dict["portfolio_id"] = portfolio_id
                            all_positions.append(pos_dict)
                    except Exception:
                        pass
            
            return {
                "status": "success",
                "positions": all_positions
            }
        except Exception as e:
            logger.error(f"Error getting open positions: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get open positions: {str(e)}"
            )