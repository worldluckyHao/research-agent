import asyncio
import logging

from sqlalchemy.exc import (
    OperationalError,
)

from backend.app.core.celery_app import (
    celery_app,
)
from backend.app.db.session import engine
from backend.app.services.paper_document_parser import (
    run_document_parse_job,
)


logger = logging.getLogger(__name__)


async def _run_document_parse(
    document_id: int,
) -> None:
    """
    Async PDF Parse 入口。
    """

    try:

        await run_document_parse_job(
            document_id=document_id
        )

    finally:

        # Windows + asyncio.run 开发模式下，
        # 释放 AsyncEngine Pool，
        # 避免跨 Event Loop 连接复用。
        await engine.dispose()


@celery_app.task(
    bind=True,

    name=(
        "research_agent."
        "document_parse.run"
    ),

    autoretry_for=(
        OperationalError,
    ),

    retry_backoff=True,

    retry_backoff_max=60,

    retry_jitter=True,

    max_retries=3,
)
def run_document_parse_task(
    self,
    document_id: int,
) -> dict:
    """
    Celery PDF Parsing Task。

    Broker 中只传 document_id，
    不传整个 PDF。
    """

    logger.info(
        (
            "PDF parse task started: "
            "document_id=%s "
            "task_id=%s"
        ),
        document_id,
        self.request.id,
    )


    asyncio.run(
        _run_document_parse(
            document_id=document_id
        )
    )


    logger.info(
        (
            "PDF parse task finished: "
            "document_id=%s "
            "task_id=%s"
        ),
        document_id,
        self.request.id,
    )


    return {
        "document_id": document_id,
    }