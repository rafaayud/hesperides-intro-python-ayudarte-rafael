from server.modules.trading.domain.aggregates.candle_buffer import CandleBuffer
from server.modules.trading.domain.value_objects import Symbol, Interval, Timestamp, Candle_static
from server.modules.trading.domain.entities import Candle

from server.modules.trading.infrastructure.binance_stream_adapter import BinanceStreamAdapter

from typing import List
import asyncio
import logging
import random
import time



REPEATS = 10
SYMBOL = Symbol("BTCUSDT")
INTERVAL = Interval.M1

TIME_CONNECTED = 5
TIME_DOWN = 1

logger = logging.getLogger(__name__)

async def test_ws_desorden(ws: BinanceStreamAdapter) -> None:


    velas: List[Candle] = []

    for i in range(REPEATS):

        logger.info(f"Test {i+1} of {REPEATS}")



        await ws.connect()
        logger.info(f"Connected to {SYMBOL} {INTERVAL}")
        start_time = time.time()
        try:

            async for candle in ws.stream_candle(SYMBOL, INTERVAL):
                print(candle)

                velas.append(candle)

                if time.time() - start_time > TIME_CONNECTED:
                    logger.info(f"Time connected to {SYMBOL} {INTERVAL} exceeded {TIME_CONNECTED} seconds")
                    break

        except Exception as e:
            logger.error(f"Error in test {i+1}: {e}")
            continue

        await ws.disconnect()


        logger.info(f"Down for {TIME_DOWN} seconds")
        await asyncio.sleep(TIME_DOWN)


    for candle in velas:
        print(candle.ohlcv.timestamp)


async def main():
    """Punto de entrada principal para ejecutar el test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    ws = BinanceStreamAdapter()
    try:
        await test_ws_desorden(ws)
    except KeyboardInterrupt:
        logger.info("Test interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error en el test: {e}", exc_info=True)
    finally:
        await ws.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
