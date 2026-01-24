# from fastapi.testclient import TestClient
# from src.api.main import app
# import websockets
# import asyncio
# import json


# client = TestClient(app)


# #TEST 1:
# #Test the sync candles endpoint.
# # def test_sync_candles() -> None:
# #     """Test the sync candles endpoint."""
# #     response = client.put("/candles/sync", json={"symbols": ["BTCUSDT", "ETHUSDT"], "intervals": ["H1", "M1"]})

# #     assert response.status_code == 200

# #     assert response.json() == {"status": "synced"}

# #TEST 2:
# #Test the stream candles endpoint.
# def test_websocket_candles() -> None:
#     with client.websocket_connect("/candles_live/BTCUSDT/M1") as ws:
#         # Recibe el primer mensaje
#         data = ws.receive_json()
#         assert "candle" in data
#         assert data["symbol"] == "BTCUSDT"
        

        
#         # Puedes recibir más mensajes
#         data2 = ws.receive_json()
#         assert "candle" in data2
