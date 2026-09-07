"""Database Connection Pool and Transaction Management."""

import logging
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

from backend.app.config import settings

logger = logging.getLogger("tool_gateway.db")

_pool: ThreadedConnectionPool | None = None


def init_db_pool(minconn: int | None = None, maxconn: int | None = None) -> ThreadedConnectionPool:
    """Initialize the global threaded connection pool."""
    global _pool
    if _pool is not None and not _pool.closed:
        return _pool

    min_c = minconn or settings.db_pool_min_conns
    max_c = maxconn or settings.db_pool_max_conns
    db_url = settings.supabase_db_url

    if not db_url:
        raise ValueError("SUPABASE_DB_URL is not configured in environment or settings.")

    logger.info("Initializing ThreadedConnectionPool (min=%d, max=%d)...", min_c, max_c)
    _pool = ThreadedConnectionPool(minconn=min_c, maxconn=max_c, dsn=db_url)
    return _pool


def close_db_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool is not None and not _pool.closed:
        logger.info("Closing ThreadedConnectionPool...")
        _pool.closeall()
        _pool = None


def get_pool() -> ThreadedConnectionPool:
    """Get the active pool or initialize on demand."""
    global _pool
    if _pool is None or _pool.closed:
        return init_db_pool()
    return _pool


@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager for acquiring a database connection from the pool.
    
    Automatically rolls back uncommitted transactions on exception and returns
    the connection back to the pool in all cases.
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    except Exception:
        if conn and not conn.closed:
            try:
                conn.rollback()
            except Exception as rb_err:
                logger.error("Error during connection rollback: %s", rb_err)
        raise
    finally:
        if pool and not pool.closed and conn and not conn.closed:
            pool.putconn(conn)


@contextmanager
def get_db_cursor(commit_on_success: bool = False) -> Generator[psycopg2.extras.RealDictCursor, None, None]:
    """Context manager for obtaining a RealDictCursor with optional auto-commit."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
            if commit_on_success:
                conn.commit()

