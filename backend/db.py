from pathlib import Path
import asyncpg

from backend.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the shared asyncpg connection pool, initializing it if needed."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    """Close the shared asyncpg connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def run_migrations() -> None:
    """Execute SQL migration files in order against the database."""
    pool = await get_pool()
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    async with pool.acquire() as conn:
        for sql_file in sql_files:
            sql = sql_file.read_text(encoding="utf-8")
            await conn.execute(sql)
