import pytest
from sqlalchemy import (
    text,
)


pytestmark = pytest.mark.integration


# ============================================================
# PostgreSQL Connection
# ============================================================

async def test_postgresql_connection(
    test_engine,
):
    """
    验证：

        pytest
            ↓
        SQLAlchemy Async
            ↓
        asyncpg
            ↓
        PostgreSQL
    """

    async with (
        test_engine.connect()
        as connection
    ):

        result = await connection.execute(
            text(
                "SELECT 1"
            )
        )


        value = result.scalar_one()


    assert value == 1


# ============================================================
# Test Database Isolation
# ============================================================

async def test_database_is_test_database(
    test_engine,
):
    """
    防止 Integration Test
    意外连接开发数据库。
    """

    async with (
        test_engine.connect()
        as connection
    ):

        result = await connection.execute(
            text(
                "SELECT current_database()"
            )
        )


        database_name = (
            result.scalar_one()
        )


    assert (
        database_name
        ==
        "research_agent_test"
    )


# ============================================================
# pgvector
# ============================================================

async def test_pgvector_extension_available(
    test_engine,
):
    """
    Research-Agent Retrieval
    依赖 pgvector。

    因此测试环境必须确认
    vector extension 可用。
    """

    async with (
        test_engine.connect()
        as connection
    ):

        result = await connection.execute(
            text(
                """
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector'
                """
            )
        )


        version = (
            result.scalar_one_or_none()
        )


    assert version is not None