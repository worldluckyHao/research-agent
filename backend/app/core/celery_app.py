from celery import Celery

from backend.app.core.config import settings


celery_app = Celery(
    "research_agent",

    broker=settings.CELERY_BROKER_URL,

    backend=settings.CELERY_RESULT_BACKEND_URL,

    include=[
        "backend.app.tasks.paper_import",
    ],
)


celery_app.conf.update(
    # JSON 更安全、跨语言兼容性更好。
    task_serializer="json",

    accept_content=[
        "json",
    ],

    result_serializer="json",

    timezone="UTC",

    enable_utc=True,

    # Worker 真正开始执行后再确认消息。
    task_acks_late=True,

    # Worker 异常退出时允许消息重新入队。
    task_reject_on_worker_lost=True,

    # Result Backend 中结果保留时间。
    result_expires=(
        settings.CELERY_RESULT_EXPIRES_SECONDS
    ),

    # 启动时主动建立 Broker 连接。
    broker_connection_retry_on_startup=True,
)