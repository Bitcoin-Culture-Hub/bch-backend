from fastapi import APIRouter
from app.redis_client import redis_client

router = APIRouter(prefix="/cache", tags=["Cache Management"])


@router.post("/clear")
async def clear_all_cache():
    """Clear all application cache"""
    await redis_client.flushdb()
    return {"ok": True, "message": "Cache cleared"}


@router.post("/clear-explore")
async def clear_explore_cache():
    """Clear only explore-related cache"""
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match="explore:*", count=100)
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break
    return {"ok": True, "message": "Explore cache cleared"}


@router.get("/stats")
async def get_cache_stats():
    """Get cache statistics"""
    info = await redis_client.info()
    return {
        "used_memory": info.get("used_memory_human"),
        "connected_clients": info.get("connected_clients"),
        "total_commands_processed": info.get("total_commands_processed"),
    }