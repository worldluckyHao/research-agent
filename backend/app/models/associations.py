from sqlalchemy import (
    Column,
    ForeignKey,
    Table,
)

from backend.app.db.base import Base


# User 收藏 Paper 的多对多中间表。
user_saved_papers = Table(
    "user_saved_papers",
    Base.metadata,

    # 指向 users.id。
    Column(
        "user_id",
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),

    # 指向 papers.id。
    Column(
        "paper_id",
        ForeignKey(
            "papers.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
)