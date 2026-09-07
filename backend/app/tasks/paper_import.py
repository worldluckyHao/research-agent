import asyncio
import logging

from sqlalchemy.exc import OperationalError

from backend.app.core.celery_app import (
    celery_app,
)
from backend.app.db.session import engine
from backend.app.services.paper_import import (
    run_paper_import_job,
)


logger = logging.getLogger(__name__)


async def _run_import_job(
    job_id: str,
) -> None:
    """
    Celery Task 的异步业务入口。

    Worker Task 本身是同步函数，
    真正的 Import Pipeline 仍保持 async。
    """

    try:
        await run_paper_import_job(
            job_id=job_id
        )

    finally:
        # asyncio.run() 每次创建独立 event loop。
        # 当前开发实现结束后释放 AsyncEngine Pool，
        # 避免连接跨 event loop 被复用。
        await engine.dispose()


@celery_app.task(
    bind=True,

    name=(
        "research_agent."
        "paper_import.run"
    ),

    # DB 临时连接异常时最多重试 3 次。
    autoretry_for=(
        OperationalError,
    ),

    retry_backoff=True,

    retry_backoff_max=60,

    retry_jitter=True,

    max_retries=3,
)
def run_paper_import_task(
    self,
    job_id: str,
) -> dict:
    """
    Celery Worker 执行论文导入。

    Celery 消息只传 job_id，
    真正 payload 从 PostgreSQL 获取。
    """

    logger.info(
        "Celery paper import started: "
        "job_id=%s task_id=%s",
        job_id,
        self.request.id,
    )

    asyncio.run(
        _run_import_job(
            job_id=job_id
        )
    )

    logger.info(
        "Celery paper import finished: "
        "job_id=%s task_id=%s",
        job_id,
        self.request.id,
    )

    return {
        "job_id": job_id,
    }