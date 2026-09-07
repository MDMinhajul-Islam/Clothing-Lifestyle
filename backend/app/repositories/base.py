"""Base Repository Class with query execution helpers."""

from typing import Any, List, Optional
import psycopg2.extensions
from psycopg2.extras import RealDictCursor


class BaseRepository:
    """Base database repository providing consistent cursor handling."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn

    def cursor(self) -> RealDictCursor:
        return self.conn.cursor(cursor_factory=RealDictCursor)
