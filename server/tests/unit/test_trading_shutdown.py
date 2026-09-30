import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from apps.api.trading_state import TradingStateManager


@pytest.mark.asyncio
async def test_shutdown_cancels_task_and_closes_connections_without_reentrancy_deadlock():
    state = TradingStateManager()
    engine = SimpleNamespace(stop=AsyncMock(), **{
        name: SimpleNamespace(disconnect=AsyncMock())
        for name in ('_stream', '_order', '_exchange', '_portfolio_manager')
    })
    started = asyncio.Event()

    async def run():
        try:
            started.set()
            await asyncio.Event().wait()
        finally:
            await state.shutdown('p')

    task = asyncio.create_task(run())
    await state.register_engine('p', engine, task)
    await started.wait()
    await asyncio.wait_for(state.shutdown_all(), timeout=1)
    assert task.cancelled()
    assert not await state.is_running('p')
    for name in ('_stream', '_order', '_exchange', '_portfolio_manager'):
        getattr(engine, name).disconnect.assert_awaited_once()
