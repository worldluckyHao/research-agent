import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)


# ============================================================
# Test Database URL
# ============================================================

@pytest.fixture
def test_database_url() -> str:
    """
    Integration Test 专用数据库。

    必须显式设置：
        TEST_DATABASE_URL

    禁止测试连接开发数据库：
        research_agent
    """

    database_url = os.getenv(
        "TEST_DATABASE_URL"
    )


    if not database_url:

        pytest.fail(
            (
                "TEST_DATABASE_URL is not configured. "
                "Integration tests must use "
                "research_agent_test."
            )
        )


    # --------------------------------------------------------
    # Safety Guard
    # --------------------------------------------------------

    database_name = (
        database_url
        .rsplit(
            "/",
            maxsplit=1,
        )[-1]
        .split(
            "?",
            maxsplit=1,
        )[0]
    )


    if database_name != "research_agent_test":

        pytest.fail(
            (
                "Unsafe integration database: "
                f"{database_name}. "
                "Expected research_agent_test."
            )
        )


    return database_url


# ============================================================
# Test Engine
# ============================================================

@pytest_asyncio.fixture
async def test_engine(
    test_database_url: str,
):
    """
    创建真正的 Async SQLAlchemy Engine。

    注意：
    这里只连接 Test Database，
    不使用生产 AsyncSessionLocal。
    """

    engine: AsyncEngine = (
        create_async_engine(
            test_database_url,

            echo=False,

            pool_pre_ping=True,
        )
    )


    try:

        yield engine


    finally:

        await engine.dispose()