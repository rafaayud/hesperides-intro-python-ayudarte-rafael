# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/server

WORKDIR /app

# Dependencias del sistema para asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
RUN pip install uv

# Copiar archivos de dependencias
COPY pyproject.toml ./
COPY uv.lock* ./

# Instalar dependencias
RUN uv pip install --system -e . 2>/dev/null || \
    uv pip install --system \
    aiohttp \
    asyncpg \
    python-dotenv \
    "fastapi[standard]" \
    matplotlib \
    "numpy==2.3.2" \
    pandas \
    plotly \
    polars \
    pytest \
    pytest-asyncio \
    python-binance \
    tenacity \
    uvicorn \
    pydantic-settings

# Copiar el código del servidor
COPY server/ ./server/

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
