import logging
from fastapi import HTTPException
from modules.trading.domain.value_objects import Symbol, Interval
from apps.api.service_factory import ServiceFactory


logger = logging.getLogger(__name__)

class CandleController:

    def serialize_candle(self, candle) -> dict:
        return {
            "open_time": candle.timestamp.timestamp.isoformat(),
            "open": float(candle.open.value),
            "high": float(candle.high.value),
            "low": float(candle.low.value),
            "close": float(candle.close.value),
            "volume": float(candle.volume.value),
        }

    async def get_candles(
        self, 
        symbol: str, 
        interval: str, 
        limit: int, 
        storage: str | None, service_factory: ServiceFactory) -> dict:
        """Get candles for a given symbol and interval"""
        logger.info(f"GET /candles/{symbol}/{interval}?limit={limit}")

        try:
            interval_enum = Interval[interval.upper()]
        except KeyError:
            valid_intervals = [i.name for i in Interval]
            #422 Unprocessable Entity, client error
            raise HTTPException(
                status_code=422, 
                detail=f"Invalid interval: '{interval}'. Valid intervals: {valid_intervals}"
            )

        try:
            storage_service = service_factory.create_data_storage_service(storage=storage)
            async with storage_service:
                candles = await storage_service.get_candles(
                    Symbol(symbol), 
                    interval_enum, 
                    limit
                )
        except Exception as e:
            logger.error(f"Error fetching candles: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Error fetching candles: {str(e)}"
            )

        return {"candles": [self.serialize_candle(candle) for candle in candles]}

    async def sync_candles(
        self, 
        request: dict, 
        service_factory: ServiceFactory
    ) -> dict:
        """Sync candles from exchange to storage"""
        logger.info(f"PUT /candles/sync")

        try:
            ingestion_service = service_factory.create_ingestion_service(
                exchange=request.get("exchange"), 
                storage=request.get("storage")
            )
            async with ingestion_service:
                await ingestion_service.sync_all(
                    [Symbol(s) for s in request["symbols"]],
                    [Interval[i.upper()] for i in request["intervals"]]
                )
        except Exception as e:
            logger.error(f"Error syncing candles: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error syncing candles: {str(e)}"
            )
        
        return {
            "status": "synced",
            "symbols": request["symbols"],
            "intervals": request["intervals"]
        }
