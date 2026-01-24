from fastapi import APIRouter
from apps.api.registry import AdapterRegistry


router = APIRouter(tags=["info"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/info/adapters")
async def list_adapters():
    """List ofthe adapters registered"""
    return {
        "exchanges": list(AdapterRegistry._exchanges.keys()),
        "storages": list(AdapterRegistry._storages.keys()),
        "streams": list(AdapterRegistry._streams.keys()),
    }