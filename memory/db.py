"""Conexión compartida a PostgreSQL para los módulos de memoria."""

import os
import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.environ["DATABASE_URL"]

_pool: psycopg2.pool.SimpleConnectionPool | None = None


def _get_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(
            1, 5, DATABASE_URL, options="-c client_encoding=UTF8"
        )
    return _pool


class _PooledConn:
    """Wrapper que devuelve la conexión al pool en lugar de cerrarla."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        return self._conn.commit()

    def close(self):
        _get_pool().putconn(self._conn)


def get_conn() -> _PooledConn:
    return _PooledConn(_get_pool().getconn())
