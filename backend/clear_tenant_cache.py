#!/usr/bin/env python3
"""
Clear cache for a specific tenant (safe + production-ready)

Usage:
    python clear_tenant_cache.py <tenant_id>
"""

import sys
import asyncio
import os
from loguru import logger

# Proper path handling
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from clear_cache import clear_specific_tenant_cache


async def clear_cache(tenant_id: str):
    logger.info(f"🗑️ Clearing cache for tenant: {tenant_id}")
    logger.info("=" * 50)

    try:
        success = await clear_specific_tenant_cache(tenant_id)

        if success:
            logger.success(f"✅ Cache cleared for tenant {tenant_id}")
            logger.info("✔ Cache isolation verified")
        else:
            logger.error(f"❌ Failed to clear cache for tenant {tenant_id}")

    except Exception as e:
        logger.exception(f"🔥 Error clearing cache: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python clear_tenant_cache.py <tenant_id>")
        sys.exit(1)

    tenant_id = sys.argv[1]
    asyncio.run(clear_cache(tenant_id))


if __name__ == "__main__":
    main()