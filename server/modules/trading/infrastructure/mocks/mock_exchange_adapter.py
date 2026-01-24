from ...domain.ports import ExchangePort
from ...domain.value_objects import Symbol, Interval, Timestamp, Candle_static, Price, Quantity
from ...domain.utils import AdapterMeta, timed_async
from decimal import Decimal
from datetime import datetime
import random
import asyncio
import logging


class MockExchangeAdapter(ExchangePort, metaclass=AdapterMeta):
    """
    Mock exchange adapter for testing.
    Generates deterministic candle data with correct chronological order.
    
    IMPORTANTE: Siempre elimina la última vela (vela actual "en vivo") 
    para simular el comportamiento real de una API que solo devuelve velas cerradas.
    """
    
    def __init__(self, base_price: float = 100.0, seed: int | None = None):
        self._base_price = base_price
        # RNG instanciado para reproducibilidad
        self._rng = random.Random(seed) if seed is not None else random.Random()
    
    async def connect(self) -> None:
        """Connect to the mock exchange (no-op)"""
        pass
    
    async def disconnect(self) -> None:
        """Disconnect from the mock exchange (no-op)"""
        pass
    
    def _generate_candle_with_price(
        self, 
        symbol: Symbol, 
        interval: Interval, 
        timestamp: datetime, 
        current_price: float
    ) -> Candle_static:
        """
        Generate a single OHLCV candle from a given price.
        
        Esta función es PURA: no modifica ningún estado de la clase.
        Toma el precio como parámetro y retorna una nueva vela.
        
        Args:
            symbol: Trading symbol
            interval: Timeframe
            timestamp: Candle open time
            current_price: Base price for this candle
            
        Returns:
            Candle_static object with generated OHLCV data
        """
        # Random price movement ±2%
        change = self._rng.uniform(-0.02, 0.02)
        close = current_price * (1 + change)
        
        # Generate OHLC ensuring proper relationships
        # high >= max(open, close) and low <= min(open, close)
        open_price = close * self._rng.uniform(0.995, 1.005)
        high = max(open_price, close) * self._rng.uniform(1.0, 1.01)
        low = min(open_price, close) * self._rng.uniform(0.99, 1.0)
        volume = self._rng.uniform(500, 1500)
        
        return Candle_static(
            symbol=symbol,
            interval=interval,
            timestamp=Timestamp(timestamp),
            open=Price(Decimal(str(round(open_price, 2)))),
            high=Price(Decimal(str(round(high, 2)))),
            low=Price(Decimal(str(round(low, 2)))),
            close=Price(Decimal(str(round(close, 2)))),
            volume=Quantity(Decimal(str(round(volume, 4)))),
        )
    
    def _interval_to_seconds(self, interval: Interval) -> int:
        """Convert Interval enum to seconds"""
        mapping = {
            Interval.M1: 60,
            Interval.M5: 300,
            Interval.M15: 900,
            Interval.H1: 3600,
            Interval.H4: 14400,
            Interval.D1: 86400,
            Interval.W1: 604800,
            Interval.MO1: 2592000,
        }
        return mapping.get(interval, 60)
    
    @timed_async
    async def get_historical_candles(
        self, 
        symbol: Symbol, 
        interval: Interval, 
        limit: int
    ) -> list[Candle_static]:
        """
        Generate historical candles in correct chronological order.
        
        IMPORTANTE: Siempre elimina la última vela generada (vela actual "en vivo")
        para simular el comportamiento de APIs reales que solo devuelven velas cerradas.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            interval: Timeframe (e.g., Interval.M1, Interval.H1)
            limit: Number of candles requested
        
        Returns:
            List of (limit - 1) closed candles in chronological order (oldest → newest)
            La última vela se elimina automáticamente porque representa la vela actual en vivo.
        
        Comportamiento:
            - Si pides 100 velas → recibes 99 (todas cerradas)
            - Si pides 1 vela → recibes 0 (porque la única vela es la actual)
        
        Example:
            ```python
            mock = MockExchangeAdapter.deterministic(seed=42)
            
            # Pedimos 100 velas
            candles = await mock.get_historical_candles(
                Symbol("BTCUSDT"), 
                Interval.M1, 
                100
            )
            
            # Recibimos 99 velas cerradas
            assert len(candles) == 99
            
            # Todas son velas cerradas (no incluye la actual en vivo)
            for candle in candles:
                assert candle.timestamp < datetime.now()
            ```
        """
        candles = []
        seconds = self._interval_to_seconds(interval)
        now = datetime.now().timestamp()
        
        # Variable LOCAL que evoluciona correctamente en el tiempo
        # No modifica self._current_price para evitar acumulación incorrecta
        price = self._base_price
        
        for i in range(limit):
            # Calcular timestamp: más antiguo primero, más reciente último
            # Ejemplo: limit=10, i=0 genera la vela más antigua, i=9 la más reciente
            ts = datetime.fromtimestamp(now - seconds * (limit - i - 1))
            
            # Generar vela usando precio específico (función pura, sin efectos secundarios)
            candle = self._generate_candle_with_price(symbol, interval, ts, price)
            candles.append(candle)
            
            # Actualizar precio LOCAL para la siguiente vela (evolución temporal correcta)
            price = float(candle.close.value)
        
        # ✅ SIEMPRE eliminar la última vela (vela "en vivo" actual)
        # En trading real, la última vela está incompleta hasta que cierre
        # Para backtesting necesitamos SOLO velas cerradas
        if len(candles) > 0:
            candles = candles[:-1]
        
        return candles
    
    async def get_candles_since(
        self, 
        symbol: Symbol, 
        interval: Interval, 
        start_time: Timestamp
    ) -> list[Candle_static]:
        """
        Get candles since start_time.
        
        Automáticamente excluye la vela actual (como get_historical_candles).
        
        Args:
            symbol: Trading symbol
            interval: Timeframe
            start_time: Start timestamp
            
        Returns:
            List of closed candles from start_time to now (excluding current candle)
        """
        seconds = self._interval_to_seconds(interval)
        now = datetime.now().timestamp()
        diff = now - start_time.timestamp.timestamp()
        num_candles = int(diff / seconds) + 1
        
        return await self.get_historical_candles(symbol, interval, num_candles)

    @classmethod
    def deterministic(cls, base_price: float = 100.0, seed: int =101) -> "MockExchangeAdapter":
        return cls(base_price, seed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    async def main():
        logger = logging.getLogger(__name__)
        adapter = MockExchangeAdapter.deterministic()
        candles = await adapter.get_historical_candles(Symbol("BTCUSDT"), Interval.M1, 10)
        
        logger.info(Candle_static._print_table(candles))
    asyncio.run(main())