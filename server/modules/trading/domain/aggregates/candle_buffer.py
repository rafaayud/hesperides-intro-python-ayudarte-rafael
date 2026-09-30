import asyncio
import time
from collections import deque
from typing import Deque, List, Optional
from datetime import datetime
import logging
from ..entities import Candle
from ..value_objects import Symbol, Interval, Timestamp, Candle_static

logger = logging.getLogger(__name__)

# ===============
# Buffer de velas
# ===============

class CandleBuffer:
    """
    Invariants:
      - closed_candles: only closed candles, immutable.
      - current_candle: current candle in progress (mutable at logical level, here we model it as immutable and replace it).
      - session_origin: reference to validate alignment: (open_time - origin) % timeframe == 0
      - is_degraded: if True, signals and orders are blocked.
    """

    def __init__(
        self,
        max_size: int = 500,
        interval: Interval = Interval.M1,
        symbol: Symbol = Symbol("BTCUSDT"),
        session_origin: Optional[Timestamp] = None,
    ) -> None:

        # FIFO O(1). NOTA: deque no soporta slicing, usa last_closed(n) o iteración.
        self.closed_candles: Deque[Candle_static] = deque(maxlen=max_size)
        self.current_candle: Optional[Candle] = None

        self.max_size = max_size
        self.timeframe_seconds = interval.seconds
        self.symbol = symbol
        self.session_origin = session_origin

        self.is_degraded = False
        self.is_recovering = False

    def on_candle_update(self, candle: Candle) -> None:
        """Updates the current candle in progress."""
        self.current_candle = candle


    def on_candle_close(self, candle_closed: Candle) -> None:
        """
        Confirms the closure of the current candle and moves it to the historical buffer.

        Raises ValueError if validation fails, the caller must:
          - marcar is_degraded=True
          - iniciar recuperación/backfill
        """
        if self.current_candle is None:
            raise ValueError("No hay vela actual para cerrar")

        # Validation 0: symbol
        if candle_closed.ohlcv.symbol != self.symbol:
            raise ValueError(f"Symbol mismatch: expected {self.symbol}, received {candle_closed.ohlcv.symbol}")

        # Validation 1: identity by open_time (no close_time)
        if candle_closed.ohlcv.timestamp != self.current_candle.ohlcv.timestamp:
            raise ValueError(
                f"Open time mismatch: expected {self.current_candle.ohlcv.timestamp}, received {candle_closed.ohlcv.timestamp}"
            )

        # Validation 2: temporal alignment with session_origin
        if self.session_origin is not None:
            # Restar datetime objects directamente, no Timestamp objects
            offset = candle_closed.ohlcv.timestamp.timestamp - self.session_origin.timestamp
            offset_seconds = int(offset.total_seconds())
            if offset_seconds % self.timeframe_seconds != 0:
                raise ValueError(
                    f"Open time no alineado: open_time={candle_closed.ohlcv.timestamp}, origin={self.session_origin}, "
                    f"offset={offset_seconds}, timeframe={self.timeframe_seconds}s"
                )

        # Validation 3: monotonicity
        if len(self.closed_candles) > 0:
            last_open = self.closed_candles[-1].timestamp
            new_open = candle_closed.ohlcv.timestamp
            # Compare datetime objects directly for accurate comparison
            if new_open.timestamp < last_open.timestamp:
                raise ValueError(
                    f"Open time no monotónico: último={last_open.timestamp}, nuevo={new_open.timestamp}"
                )
            # Si son iguales, es la misma vela, no la añadimos de nuevo
            elif new_open.timestamp == last_open.timestamp:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Duplicate candle timestamp: {new_open.timestamp}, skipping")
                self.current_candle = None
                return

        candle_closed_static = candle_closed.static_candle
        

        self.closed_candles.append(candle_closed_static)
        self.current_candle = None

    def can_trade(self) -> bool:
        """If is_degraded=True, the strategy does not emit signals and the executor rejects orders."""
        return not self.is_degraded

    def get_closed_candles(self) -> Deque[Candle_static]:
        """Reference to closed candles (without copy)."""
        return self.closed_candles

    def get_current_candle(self) -> Optional[Candle]:
        return self.current_candle

    def last_closed(self, n: int) -> List[Candle_static]:
        """
        Last n closed candles as list.
        Cost O(n) by conversion, use it only when needed (windows).
        """
        if n <= 0:
            return []
        if n >= len(self.closed_candles):
            return list(self.closed_candles)
        return list(self.closed_candles)[-n:]

    # ==================
    # Warm-up & Recovery
    # ==================

    def warm_up(self, candles: List[Candle_static]) -> None:
        """
        Initialize buffer with historical candles.
        
        Args:
            candles: List of closed candles, sorted by time (oldest first)
        """
        self.closed_candles.clear()
        self.current_candle = None
        
        
        for candle in candles:
            # Validate symbol
            if candle.symbol != self.symbol:
                raise ValueError(f"Symbol mismatch: expected {self.symbol}, got {candle.symbol}")
            
            # Validate monotonicity
            if len(self.closed_candles) > 0:
                last_timestamp = self.closed_candles[-1].timestamp.timestamp
                new_timestamp = candle.timestamp.timestamp
                if new_timestamp <= last_timestamp:
                    raise ValueError(
                        f"Warm-up candles not monotonic: último={self.closed_candles[-1].timestamp.timestamp}, "
                        f"nuevo={candle.timestamp.timestamp}"
                    )
            
            self.closed_candles.append(candle)
        
        self.is_degraded = False

    def recover(self, candles: List[Candle_static]) -> None:
        """
        Recover buffer with historical candles.
        
        Args:
            candles: List of closed candles, sorted by time (oldest first)
        """
        self.closed_candles.clear()
        self.current_candle = None
        self.warm_up(candles)

        self.mark_recovered()
        

    def is_ready(self, min_candles: int) -> bool:
        """Check if buffer has enough candles for trading."""
        return len(self.closed_candles) >= min_candles

    def mark_degraded(self, reason: str) -> None:
        """Mark buffer as degraded (stops trading)."""
        self.is_degraded = True

    def mark_recovered(self) -> None:
        """Mark buffer as recovered."""
        self.is_degraded = False
        self.is_recovering = False

    def __len__(self) -> int:
        """Number of closed candles."""
        return len(self.closed_candles)
    
    
    # =========================
    # Feed Integration Helpers
    # =========================
    
    def _check_gap_and_alignment(
        self,
        last_open_time: int,
        new_open_time: int) -> str:
        """
        Check gap and alignment between candles.
        
        Returns: "CONTINUOUS", "GAP", "MISALIGNED", "OUT_OF_ORDER"
        """
        expected_next = last_open_time + self.timeframe_seconds
        
        if new_open_time == expected_next:
            return "CONTINUOUS"
        if new_open_time > expected_next:
            gap_size = new_open_time - expected_next
            if gap_size % self.timeframe_seconds != 0:
                return "MISALIGNED"
            return "GAP"
        return "OUT_OF_ORDER"
    
    def check_feed_health(self, tolerance_seconds: int = 10) -> str:
        """
        Detect feed delay, does NOT close candles artificially.
        
        Returns: "OK" or "STALE"
        """
        if self.current_candle is None:
            return "OK"
        
        # Get current candle's open time in seconds
        current_open_seconds = int(self.current_candle.ohlcv.timestamp.timestamp.timestamp())
        expected_close_seconds = current_open_seconds + self.timeframe_seconds
        now_seconds = int(time.time())
        
        if now_seconds > expected_close_seconds + tolerance_seconds:
            self.is_degraded = True
            logger.warning(
                f"Feed stale: current_candle opened at {self.current_candle.ohlcv.timestamp.timestamp}, "
                f"expected close at {datetime.fromtimestamp(expected_close_seconds)}, "
                f"now is {datetime.fromtimestamp(now_seconds)}"
            )
            return "STALE"
        
        return "OK"

