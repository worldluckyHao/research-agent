import asyncio
import logging

from sqlalchemy.exc import (
    OperationalError,
)

from backend.app.core.celery_app import (
    celery_app,
)
from backend.app.db.session import (
    engine,
)
from backend.app.services.paper_document_embedder import (
    run_document_embedding_job,
)


logger = logging.getLogger(__name__)


async def _run_document_embedding(
    document_id: int,
) -> None:
    """
    Async Embedding Job 入口。
    """

    try:

        await run_document_embedding_job(
            document_id=document_id
        )

    finally:

        # Windows + asyncio.run
        # 开发模式下释放 AsyncEngine Pool。
        await engine.dispose()


@celery_app.task(
    bind=True,

    name=(
        "research_agent."
        "document_embed.run"
    ),

    autoretry_for=(
        OperationalError,
    ),

    retry_backoff=True,

    retry_backoff_max=60,

    retry_jitter=True,

    max_retries=3,
)
def run_document_embedding_task(
    self,
    document_id: int,
) -> dict:
    """
    Celery Embedding Task。

    Broker 只传：
        document_id

    不传：
        Chunk Text
        Vector
    """

    logger.info(
        (
            "Document embedding task started: "
            "document_id=%s "
            "task_id=%s"
        ),
        document_id,
        self.request.id,
    )


    asyncio.run(
        _run_document_embedding(
            document_id=document_id
        )
    )


    logger.info(
        (
            "Document embedding task finished: "
            "document_id=%s "
            "task_id=%s"
        ),
        document_id,
        self.request.id,
    )


    return {
        "document_id": document_id,
    }