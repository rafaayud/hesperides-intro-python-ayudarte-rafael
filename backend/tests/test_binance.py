# test_binance_api.py
import asyncio
import aiohttp
import json

async def ver_klines_simple():
    """Ejemplo simple para ver qué devuelve Binance"""
    
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "limit": 3  # Solo 3 para ver claramente
    }
    
    print("🔍 Llamando a Binance API...")
    print(f"URL: {url}")
    print(f"Params: {params}\n")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            print(f"Status Code: {response.status}")
            print(f"Headers: {dict(response.headers)}\n")
            
            # Obtener los datos
            data = await response.json()
            
            # Ver el JSON completo
            print("=" * 80)
            print("RESPUESTA COMPLETA (JSON):")
            print("=" * 80)
            print(json.dumps(data, indent=2))
            print("\n")
            
            # Analizar cada kline
            print("=" * 80)
            print("DESGLOSE DE CADA KLINE:")
            print("=" * 80)
            
            for i, kline in enumerate(data, 1):
                print(f"\n📊 KLINE #{i}")
                print(f"   [0] Open time:       {kline[0]} → {from_timestamp(kline[0])}")
                print(f"   [1] Open:            {kline[1]}")
                print(f"   [2] High:            {kline[2]}")
                print(f"   [3] Low:             {kline[3]}")
                print(f"   [4] Close:           {kline[4]}")
                print(f"   [5] Volume:          {kline[5]}")
                print(f"   [6] Close time:      {kline[6]} → {from_timestamp(kline[6])}")
                print(f"   [7] Quote volume:    {kline[7]}")
                print(f"   [8] Number trades:   {kline[8]}")
                print(f"   [9] Taker buy base:  {kline[9]}")
                print(f"   [10] Taker buy quote: {kline[10]}")
                print(f"   [11] Ignore:          {kline[11]}")
            
            return data

def from_timestamp(ts):
    """Convierte timestamp a fecha legible"""
    from datetime import datetime
    return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    asyncio.run(ver_klines_simple())
