from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
# pyright: ignore [reportMissingImports]
from src.config.database import get_session
import time

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health():
    """
    Lightweight health check — no DB required.

    Used by Docker HEALTHCHECK and container startup probes.
    Returns HTTP 200 immediately to signal the process is alive.
    """
    return {"success": True, "data": {"status": "ok"}, "meta": {}}


@router.get("/db")
async def health_db(session: AsyncSession = Depends(get_session)):
    """
    Database health check.

    Returns connection pool stats, query latency, and pgvector extension status.
    Always returns HTTP 200; check `status` field for health state.
    """
    start_time = time.time()
    try:
        await session.execute(text("SELECT 1"))

        pool_query = """
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE state = 'active') AS active,
          COUNT(*) FILTER (WHERE state = 'idle') AS idle,
          COUNT(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction
        FROM pg_stat_activity
        WHERE datname = current_database();
        """
        pool_result = await session.execute(text(pool_query))
        pool_stats = pool_result.mappings().first()

        ext_result = await session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector';")
        )
        has_pgvector = ext_result.scalar() is not None

        latency = round((time.time() - start_time) * 1000, 2)

        return {
            "success": True,
            "data": {
                "status": "healthy",
                "latency_ms": latency,
                "connection_pool": {
                    "total": int(pool_stats["total"]) if pool_stats else 0,
                    "active": int(pool_stats["active"]) if pool_stats else 0,
                    "idle": int(pool_stats["idle"]) if pool_stats else 0,
                    "idle_in_transaction": int(pool_stats["idle_in_transaction"]) if pool_stats else 0,
                },
                "extensions": {
                    "pgvector": "enabled" if has_pgvector else "not_installed"
                },
            },
            "meta": {},
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_DB_HEALTH_ERROR",
                "message": str(e),
            },
        }
