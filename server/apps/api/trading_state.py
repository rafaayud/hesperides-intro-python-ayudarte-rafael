import asyncio
from asyncio import Task, Lock
from typing import Dict, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from modules.trading.application.services.portfolio_manager import PortfolioManager
    from modules.trading.application.services.trading_engine import TradingEngine


logger = logging.getLogger(__name__)

class TradingStateManager:

    def __init__(self) -> None:

        self._active_engines: Dict[str, "TradingEngine"] = {}
        self._tasks: Dict[str, Task] = {}
        self._lock = Lock()


    async def register_engine(self, portfolio_id: str, engine: "TradingEngine", task: Task) -> None:
        """Register a trading engine for a portfolio"""
        async with self._lock:
            self._active_engines[portfolio_id] = engine
            self._tasks[portfolio_id] = task
            logger.info(f"Engine registered for portfolio {portfolio_id}")

    
    async def unregister_engine(self, portfolio_id: str) -> None:
        """Unregister a trading engine for a portfolio"""
        async with self._lock:
            self._active_engines.pop(portfolio_id, None)
            self._tasks.pop(portfolio_id, None)
            logger.info(f"Engine unregistered for portfolio {portfolio_id}")


    async def is_running(self, portfolio_id: str) -> bool:
        """Check if a trading engine is running for a portfolio"""
        async with self._lock:
            return portfolio_id in self._active_engines
    

    async def get_engine(self, portfolio_id: str) -> "TradingEngine":
        """Get a trading engine for a portfolio"""
        async with self._lock:
            return self._active_engines[portfolio_id]


    async def get_task(self, portfolio_id: str) -> Optional[Task]:
        """Get the background Task associated with a portfolio (if any)."""
        async with self._lock:
            return self._tasks.get(portfolio_id)


#============= SHUTDOWN =============
    async def shutdown(self, portfolio_id: str) -> bool:
        # Remove ownership first: a cancelled task also calls shutdown in finally.
        async with self._lock:
            engine = self._active_engines.pop(portfolio_id, None)
            task = self._tasks.pop(portfolio_id, None)
        if engine is None:
            return False

        await engine.stop()
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        for adapter in (engine._stream, engine._order, engine._exchange, engine._portfolio_manager):
            if adapter is not None:
                try:
                    await adapter.disconnect()
                except Exception as exc:
                    logger.error("Error disconnecting %s for %s: %s", type(adapter).__name__, portfolio_id, exc)
        return True

    async def shutdown_all(self) -> None:
        async with self._lock:
            portfolio_ids = list(self._active_engines)
        for portfolio_id in portfolio_ids:
            await self.shutdown(portfolio_id)
        logger.info("All trading engines shutdown")
