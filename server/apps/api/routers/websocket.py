from fastapi import APIRouter, WebSocket, Query
from apps.api.controllers.websocket_controller import WebSocketController
from apps.api.dependencies import get_service_factory_from_websocket

router = APIRouter(tags=["websocket"])
controller = WebSocketController()


@router.websocket("/live_candles/{symbol}/{interval}")
async def stream_candles(
    websocket: WebSocket, 
    symbol: str, 
    interval: str, 
    exchange: str = Query(default="binance")
):
    """Stream of candles in real time via WebSocket"""
    service_factory = get_service_factory_from_websocket(websocket)
    await controller.stream_candles(websocket, symbol, interval, exchange, service_factory)
    