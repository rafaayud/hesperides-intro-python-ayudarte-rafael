from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ==========================================================================
    # Default Adapters
    # ==========================================================================
    default_exchange: str = "binance"
    default_storage: str = "postgres"
    default_stream: str = "binance"
    default_order: str = "binance"
    default_portfolio_storage: str = "postgres"

    # ==========================================================================
    # Database
    # ==========================================================================
    database_url: str = "postgresql://postgres:postgres@localhost:5432/trading"

    # ==========================================================================
    # Binance API (Paper Trading / Testnet)
    # ==========================================================================
    binance_api_key: Optional[str] = Field(default=None, alias="BINANCE_API_KEY")
    binance_secret_key: Optional[str] = Field(default=None, alias="BINANCE_SECRET_KEY")
    binance_testnet: bool = Field(default=True, alias="BINANCE_TESTNET")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
