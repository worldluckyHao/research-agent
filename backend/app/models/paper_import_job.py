from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.app.db.base import Base


class PaperImportJob(Base):
    """
    Paper Import 后台任务状态。

    今天使用 FastAPI BackgroundTasks 执行。
    Day22 可以将执行器迁移到 Celery，
    而 Job 数据模型仍然继续复用。
    """

    __tablename__ = "paper_import_jobs"

    __table_args__ = (
        CheckConstraint(
            (
                "status IN "
                "('pending', 'running', 'succeeded', 'failed')"
            ),
            name="ck_paper_import_jobs_status",
        ),

        Index(
            "ix_paper_import_jobs_user_created",
            "user_id",
            "created_at",
        ),
    )


    # UUID 字符串。
    # 避免暴露连续整数 Job ID。
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )


    # 谁创建的 Import Job。
    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    # 可选：导入成功后自动加入哪个 Project。
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "research_projects.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )


    # pending -> running -> succeeded / failed
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )


    # 保存 UnifiedPaperMetadata。
    #
    # BackgroundTasks 执行时只需要 job_id，
    # 再从数据库读取 payload。
    paper_payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )


    # 导入成功后的本地 Paper ID。
    paper_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "papers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )


    # 对外只保存安全的错误摘要，
    # 完整 traceback 写入服务端日志。
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )