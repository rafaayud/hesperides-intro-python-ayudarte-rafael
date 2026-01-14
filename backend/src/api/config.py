from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Defaults
    default_exchange: str = "binance"
    default_storage: str = "postgres"
    
    # Database
    database_url: str = "postgresql://postgres:1234@localhost:5432/postgres"
    
    # Podríamos añadir más config
    # redis_url: str = "redis://localhost:6379"
    # api_keys, etc.
    
    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()