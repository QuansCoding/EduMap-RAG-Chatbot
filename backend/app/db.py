from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: ConnectionPool | None = None


def open_pool() -> None:
    """Creates global connection pool (called once at app startup)"""
    global _pool
    if _pool is None:
     _pool = ConnectionPool(
        conninfo=get_settings().database_url,
        min_size=1,
        max_size=5,  # the free Supabase pooler allows a limited # of connections
        kwargs={"row_factory": dict_row},  #rows come back as dicts : row ["title"]
        check=ConnectionPool.check_connection,  #replaces connections that the pooler closed
        open=True,
     )


def close_pool() -> None:
   global _pool
   if _pool is not None:
      _pool.close()
      _pool = None


@contextmanager
def get_conn() -> Iterator[Connection]:
    """Borrow a connection. The `with` block is one transaction:
    commit on success, rollback on exception, then return the connection to the pool."""
    if _pool is None:
        open_pool()
    assert _pool is not None
    with _pool.connection() as conn:
        yield conn


def to_pgvector(values: list[float]) ->str:
    """Format a Python list as a pgvector's text format: '[0,1,0,2,....]'.
    In SQL, casts it together as '%s::vector' """
    return "[" + ",".join(f"{v:.7f}" for v in values) + "]"