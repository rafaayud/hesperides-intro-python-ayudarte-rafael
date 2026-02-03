from apps.api.service_factory import ServiceFactory
from apps.api.schemas.backtest import BacktestRequest
from modules.trading.domain.value_objects import Symbol, Interval
from modules.trading.application.services.strategy_factory import StrategyFactory
import logging
from fastapi import HTTPException


logger = logging.getLogger(__name__)


class BacktestController:

    async def backtest(self, backtest_request: BacktestRequest, service_factory: ServiceFactory) -> dict:
        """
        Backtest a strategy: first sync data, then run backtest
        """
        symbol = Symbol(backtest_request.symbol)
        interval = Interval(backtest_request.interval)
        
        logger.info(f"Backtesting {backtest_request.strategy} on {symbol} [{interval.value}]")

        try:
            # 1. Sync data from exchange before backtest
            logger.info(f"Syncing data for {symbol} [{interval.value}]...")
            ingestion_service = service_factory.create_ingestion_service()
            async with ingestion_service:
                await ingestion_service.sync_all([symbol], [interval])
            logger.info("Data synced successfully")

            # 2. Run backtest with fresh data
            backtest_service = service_factory.create_backtest_service()
            async with backtest_service as bt:
                
                symbol = Symbol(backtest_request.symbol)
                interval = Interval(backtest_request.interval)
                candles = await bt.get_candles(symbol, interval)

                strategy = StrategyFactory.create_strategy(backtest_request.strategy, backtest_request.strategy_params)
                result = bt.test_strategy(strategy, candles, backtest_request.initial_capital)
            
            # 3. Build response with candles for chart
            response = result.to_dict()
            response["candles"] = [
                {
                    "time": int(c.timestamp.timestamp.timestamp()),
                    "open": float(c.open.value),
                    "high": float(c.high.value),
                    "low": float(c.low.value),
                    "close": float(c.close.value),
                    "volume": float(c.volume.value),
                }
                for c in candles
            ]
            return response

        except Exception as e:
            logger.error(f"Error backtesting strategy: {e}")
            raise HTTPException(status_code=500, detail=str(e))


