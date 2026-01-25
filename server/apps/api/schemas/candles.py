"""Pydantic schemas for candles endpoints"""
from pydantic import BaseModel


class SyncRequest(BaseModel):
    """Request to sync candles from exchange to storage"""
    symbols: list[str] = ["BTCUSDT"]
    intervals: list[str] = ["H1"]
    exchange: str | None = None
    storage: str | None = None

