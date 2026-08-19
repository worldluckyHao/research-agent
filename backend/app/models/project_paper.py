from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.app.db.base import Base


class ProjectPaper(Base):
    """
    Project 和 Paper 的关联对象。

    与普通中间表相比，可以保存 added_at 等关系元数据。
    """

    __tablename__ = "project_papers"

    # 同一个 Paper 在同一个 Project 中只能出现一次。
    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "research_projects.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    paper_id: Mapped[int] = mapped_column(
        ForeignKey(
            "papers.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    # Paper 加入 Project 的时间。
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # 关联的 Project。
    project: Mapped["ResearchProject"] = relationship(
        back_populates="paper_links",
    )

    # 关联的 Paper。
    paper: Mapped["Paper"] = relationship(
        back_populates="project_links",
    )