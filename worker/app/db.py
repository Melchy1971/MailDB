"""Synchronous psycopg2 connection for Celery tasks.

Uses the same DATABASE_URL as the backend but replaces the asyncpg driver
prefix so psycopg2 can parse it.
"""

from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection

from app.core.config import settings

# Strip asyncpg driver prefix → plain postgresql:// DSN
_DSN = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


@contextmanager
def get_conn() -> Generator[PgConnection, None, None]:
    conn = psycopg2.connect(_DSN)
    conn.autocommit = False
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
