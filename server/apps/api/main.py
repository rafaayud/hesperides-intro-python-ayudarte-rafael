from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .registry import AdapterRegistry
from .dependencies import setup_registry
from .service_factory import ServiceFactory
from .routers import candles, websocket, info

logger = logging.getLogger(__name__)


# ============ LIFESPAN (startup/shutdown) ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    setup_registry(settings)
    app.state.settings = settings
    app.state.services = ServiceFactory(AdapterRegistry, settings)
    logger.info("✅ Registry and services initialized")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down...")


app = FastAPI(
    title="Crypto Trading API",
    description="API for crypto trading operations",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ ROUTERS ============
app.include_router(info.router)
app.include_router(candles.router)
app.include_router(websocket.router)
