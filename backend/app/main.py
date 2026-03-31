import sys
import asyncio
import json

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import os
import time

from app.core.redis_client import redis_client
from .monitoring.middleware import PerformanceMonitoringMiddleware

# Routers
from .api.v1 import (
    users_lightning,
    cities,
    city_access_fast,
    city_access_fixed,
    departments,
    profile,
    company_settings,
    auth_info,
    bootstrap,
    health,
    persistent_auth,
    dashboard,
    login,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ✅ FIXED: Tenant-aware cache invalidation
async def cache_invalidation_listener():
    from .core.auth import invalidate_user_cache
    from .core.cache import invalidate_tenant_cache  # 👈 NEW

    if not redis_client.is_connected:
        logger.info("Redis not connected - skipping listener")
        return

    try:
        pubsub = await redis_client.subscribe("auth_cache_invalidate")

        logger.info("✅ Cache listener started")

        async for message in pubsub.listen():
            try:
                if message and message.get("type") == "message":
                    raw_data = message.get("data")

                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")

                    # ✅ FIX: Expect structured payload
                    data = json.loads(raw_data)

                    user_id = data.get("user_id")
                    tenant_id = data.get("tenant_id")

                    if user_id:
                        invalidate_user_cache(user_id)

                    if tenant_id:
                        # 🔥 CRITICAL FIX
                        await invalidate_tenant_cache(tenant_id)

                    logger.info(
                        f"🔄 Cache invalidated | user={user_id} tenant={tenant_id}"
                    )

            except Exception as e:
                logger.error(f"Listener error: {e}")

    except Exception as e:
        logger.error(f"Cache listener failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")

    # Supabase
    try:
        from .core.supabase_connection_pool import supabase_pool
        await supabase_pool.initialize()
        logger.info("✅ Supabase pool ready")
    except Exception as e:
        logger.error(f"Supabase error: {e}")

    # Redis
    try:
        await redis_client.initialize()
    except Exception as e:
        logger.warning(f"Redis warning: {e}")

    # ✅ FIX: Start listener safely
    if redis_client.is_connected:
        asyncio.create_task(cache_invalidation_listener())

    yield

    logger.info("Shutting down...")


app = FastAPI(
    title="PropertyFlow API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Monitoring
app.add_middleware(PerformanceMonitoringMiddleware)


# Routers
app.include_router(login.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(users_lightning.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(cities.router, prefix="/api/v1")
app.include_router(city_access_fast.router, prefix="/api/v1")
app.include_router(city_access_fixed.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
app.include_router(company_settings.router, prefix="/api/v1")
app.include_router(bootstrap.router, prefix="/api/v1")
app.include_router(auth_info.router, prefix="/api/v1")
app.include_router(persistent_auth.router, prefix="/api/v1/auth")
app.include_router(health.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}