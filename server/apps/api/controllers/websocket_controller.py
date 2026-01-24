from fastapi import WebSocket, WebSocketDisconnect
from modules.trading.domain.value_objects import Symbol, Interval
from apps.api.service_factory import ServiceFactory
import logging

logger = logging.getLogger(__name__)

class WebSocketController:

    async def stream_candles(
        self, 
        websocket: WebSocket, 
        symbol: str, 
        interval: str, 
        exchange: str,
        service_factory: ServiceFactory) -> None:
        """
        Stream candles in real time via WebSocket
        Args:
            websocket: WebSocket instance
            symbol: Symbol to stream
            interval: Interval to stream
            exchange: Exchange to stream
            service_factory: ServiceFactory instance
        """
        await websocket.accept()
        
        try:
            interval_enum = Interval[interval.upper()]
        except KeyError:
            valid_intervals = [i.name for i in Interval]
            await websocket.close(code=1008, reason=f"Invalid interval: '{interval}'. Valid intervals: {valid_intervals}")
            return

        try:
            streaming_service = service_factory.create_streaming_service(exchange=exchange)
            async with streaming_service:
                async for candle in streaming_service.stream_candle(Symbol(symbol), interval_enum):
                    await websocket.send_json({
                        "symbol": symbol,
                        "interval": interval,
                        "candle": {
                            "open_time": candle.open_time.timestamp.isoformat(),
                            "open": float(candle.ohlcv.open.value),
                            "high": float(candle.ohlcv.high.value),
                            "low": float(candle.ohlcv.low.value),
                            "close": float(candle.ohlcv.close.value),
                            "volume": float(candle.ohlcv.volume.value),
                            "is_closed": candle.is_closed
                        }
                    })
        except WebSocketDisconnect:
            logger.info(f"Client disconnected from {symbol}/{interval}")
        except Exception as e:
            logger.error(f"Error in stream: {e}", exc_info=True)
            await websocket.close(code=1011, reason=f"Error: {str(e)}")
