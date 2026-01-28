import logging
import asyncio
from asyncio import Lock
from typing import Dict, Optional
from fastapi import HTTPException
from apps.api.service_factory import ServiceFactory

logger = logging.getLogger(__name__)


class TradingController:
    """Controller for trading operations"""
    
    # Store active trading engines by portfolio_id
    _active_engines: Dict[str, any] = {}
    _engine_tasks: Dict[str, asyncio.Task] = {}

    _active_engines_lock = Lock()
    _engine_tasks_lock = Lock()
    
    async def start_trading(self, portfolio_id: str, service_factory: ServiceFactory) -> dict:
        """
        Start trading for a portfolio.
        
        Args:
            portfolio_id: ID of the portfolio to start trading
            service_factory: Factory to create services
            
        Returns:
            dict: Trading engine status
        """
        try:
            # Check if trading is already running for this portfolio
            if portfolio_id in self._active_engines:
                return {
                    "status": "already_running",
                    "portfolio_id": portfolio_id,
                    "message": "Trading is already running for this portfolio"
                }
            
            # 1. Create portfolio manager and load portfolio
            portfolio_manager = service_factory.create_portfolio_manager()
            await portfolio_manager.connect()
            
            try:
                portfolio = await portfolio_manager.load_portfolio(portfolio_id)
            except ValueError as e:
                await portfolio_manager.disconnect()
                raise HTTPException(
                    status_code=404,
                    detail=f"Portfolio not found: {str(e)}"
                )
            
            # 2. Create trading engine with portfolio manager
            engine = service_factory.create_trading_engine(
                exchange=None,  # Use defaults
                stream=None,
                order=None, portfolio_manager=portfolio_manager)
            
            # 3. Connect engine adapters
            await engine._exchange.connect()
            await engine._stream.connect()
            await engine._order.connect()
            
            # 4. Startup engine (restore state and warm-up traders)
            await engine.startup()
            
            # 5. Start trading in background task (engine_task)
            # Esto permite que el trading corra en background sin bloquear la respuesta HTTP
            async def run_trading():
                try:
                    await engine.run()  # Este método es un loop infinito
                except Exception as e:
                    logger.error(f"Trading engine error for {portfolio_id}: {e}", exc_info=True)
                finally:
                    # Cleanup on exit
                    if portfolio_id in self._active_engines:
                        async with self._active_engines_lock:
                            del self._active_engines[portfolio_id]
                    if portfolio_id in self._engine_tasks:
                        async with self._engine_tasks_lock:
                            del self._engine_tasks[portfolio_id]
                    await engine.stop()
                    await engine._stream.disconnect()
                    await engine._order.disconnect()
                    await engine._exchange.disconnect()
                    await portfolio_manager.disconnect()
            
            # Crear tarea en background y guardarla
            task = asyncio.create_task(run_trading())
            async with self._active_engines_lock:
                self._active_engines[portfolio_id] = engine
            async with self._engine_tasks_lock:
                self._engine_tasks[portfolio_id] = task
            
            logger.info(f"Trading started for portfolio {portfolio_id}")
            
            return {
                "status": "started",
                "portfolio_id": portfolio_id,
                "message": "Trading engine started successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting trading for {portfolio_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start trading: {str(e)}"
            )
                
    
    async def stop_trading(self, portfolio_id: str, service_factory: ServiceFactory) -> dict:
        """
        Stop trading for a portfolio.
        
        Args:
            portfolio_id: ID of the portfolio to stop trading
            service_factory: Factory to create services
            
        Returns:
            dict: Trading engine status
        """
        try:
            if portfolio_id not in self._active_engines:
                return {
                    "status": "not_running",
                    "portfolio_id": portfolio_id,
                    "message": "Trading is not running for this portfolio"
                }
            
            # Get engine and stop it
            async with self._active_engines_lock:
                engine = self._active_engines[portfolio_id]
            await engine.stop()
            
            # Cancel task if it exists
            if portfolio_id in self._engine_tasks:
                async with self._engine_tasks_lock:
                    task = self._engine_tasks[portfolio_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            logger.info(f"Trading stopped for portfolio {portfolio_id}")
            
            return {
                "status": "stopped",
                "portfolio_id": portfolio_id,
                "message": "Trading engine stopped successfully"
            }
            
        except Exception as e:
            logger.error(f"Error stopping trading for {portfolio_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stop trading: {str(e)}"
            )
    
    async def get_trading_status(self, portfolio_id: str, service_factory: ServiceFactory) -> dict:
        """
        Get trading status for a portfolio.
        
        Args:
            portfolio_id: ID of the portfolio
            service_factory: Factory to create services
            
        Returns:
            dict: Trading engine status
        """
        try:
            is_running = portfolio_id in self._active_engines
            
            status_info = {
                "portfolio_id": portfolio_id,
                "is_running": is_running,
                "status": "running" if is_running else "stopped"
            }
            
            if is_running:
                async with self._active_engines_lock:
                    engine = self._active_engines[portfolio_id]
                task = self._engine_tasks.get(portfolio_id)
                
                status_info.update({
                    "running": engine._running if hasattr(engine, '_running') else False,
                    "task_done": task.done() if task else False,
                    "traders_count": len(engine._portfolio_manager.traders) if hasattr(engine, '_portfolio_manager') else 0
                })
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting trading status for {portfolio_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get trading status: {str(e)}"
            )
    
    async def get_active_portfolio(self, portfolio_id: str, service_factory: ServiceFactory) -> dict:
        """
        Get active portfolio with their details.
        Returns portfolio from active trading engine if running, otherwise from database.
        """
        try:
            if portfolio_id not in self._active_engines:
                raise HTTPException(
                    status_code=404,
                    detail=f"Portfolio not found: {portfolio_id}"
                )
            
            async with self._active_engines_lock:
                engine = self._active_engines[portfolio_id]

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
        pass
    
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

