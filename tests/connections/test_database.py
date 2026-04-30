"""Connection tests for database backends."""
import asyncio
import os

import pytest

pytestmark = pytest.mark.connection


@pytest.mark.asyncio
async def test_sqlite_read_write():
    """Verifies the default SQLite database is readable and writable."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/ad_synth.db")
    if not db_url.startswith("sqlite"):
        pytest.skip("DATABASE_URL is not SQLite — see test_postgresql_connection")

    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS _connection_test (id INTEGER PRIMARY KEY, val TEXT)"
            ))
            await conn.execute(text("INSERT INTO _connection_test (val) VALUES ('ping')"))
            result = await conn.execute(text("SELECT val FROM _connection_test WHERE val='ping' LIMIT 1"))
            row = result.fetchone()
            assert row is not None and row[0] == "ping"
            await conn.execute(text("DROP TABLE _connection_test"))
        print("\n  SQLite: read/write/drop ✓")
        print(f"  URL: {db_url}")
        print("  Status: SQLITE CONNECTED ✓")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_adk_database_read_write():
    """Verifies the ADK sessions database is accessible."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    db_url = os.environ.get("ADK_DATABASE_URL", "sqlite+aiosqlite:///./data/adk_sessions.db")
    if not db_url.startswith("sqlite"):
        pytest.skip("ADK_DATABASE_URL is not SQLite")

    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        print(f"\n  ADK DB: {db_url}")
        print("  Status: ADK DATABASE CONNECTED ✓")
    finally:
        await engine.dispose()


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"),
    reason="DATABASE_URL is not PostgreSQL",
)
@pytest.mark.asyncio
async def test_postgresql_connection():
    """Verifies PostgreSQL connection when DATABASE_URL points to Postgres."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"\n  PostgreSQL version: {version[:40]}")
            print("  Status: POSTGRESQL CONNECTED ✓")
    except Exception as e:
        pytest.fail(f"PostgreSQL connection failed: {e}")
    finally:
        await engine.dispose()
