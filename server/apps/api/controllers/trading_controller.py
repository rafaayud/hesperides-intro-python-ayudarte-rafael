import logging
import asyncio
from asyncio import Lock
from typing import Dict, Optional
from fastapi import HTTPException
from apps.api.service_factory import ServiceFactory
from apps.api.trading_state import TradingStateManager

logger = logging.getLogger(__name__)


class TradingController:
    """Controller for trading operations"""
    
    
    async def start_trading(self, portfolio_id: str, service_factory: ServiceFactory, trading_state: TradingStateManager) -> dict:
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
            if await trading_state.is_running(portfolio_id):
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
                    await trading_state.shutdown(portfolio_id)
            
            # Crear tarea en background y guardarla
            task = asyncio.create_task(run_trading())
            await trading_state.register_engine(portfolio_id, engine, task)
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
                
    
    async def stop_trading(self, portfolio_id: str, service_factory: ServiceFactory, trading_state: TradingStateManager) -> dict:
        """
        Stop trading for a portfolio.
        
        Args:
            portfolio_id: ID of the portfolio to stop trading
            service_factory: Factory to create services
            
        Returns:
            dict: Trading engine status
        """
        try:
            if not await trading_state.is_running(portfolio_id):
                return {
                    "status": "not_running",
                    "portfolio_id": portfolio_id,
                    "message": "Trading is not running for this portfolio"
                }
            
            # Get engine and stop it


            await trading_state.shutdown(portfolio_id)
            
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
    
    async def get_trading_status(self, portfolio_id: str, service_factory: ServiceFactory, trading_state: TradingStateManager) -> dict:
        """
        Get trading status for a portfolio.
        
        Args:
            portfolio_id: ID of the portfolio
            service_factory: Factory to create services
            
        Returns:
            dict: Trading engine status
        """
        try:
            is_running = await trading_state.is_running(portfolio_id)
            
            status_info = {
                "portfolio_id": portfolio_id,
                "is_running": is_running,
                "status": "running" if is_running else "stopped"
            }
            
            if is_running:
                engine = await trading_state.get_engine(portfolio_id)
                task = await trading_state.get_task(portfolio_id)
                
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
    


