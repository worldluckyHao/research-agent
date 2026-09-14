from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.app.db.base import Base
from backend.app.models.associations import (
    user_saved_papers,
)


class Paper(Base):
    """
    Research-Agent 中的统一论文实体。

    Paper 既可以由用户手动创建，
    也可以由 Crossref / arXiv / OpenAlex
    等外部数据源导入。
    """

    __tablename__ = "papers"

    __table_args__ = (
        # DOI 是重要的论文强标识符。
        UniqueConstraint(
            "doi",
            name="uq_papers_doi",
        ),

        # arXiv ID 同样作为唯一外部标识符。
        UniqueConstraint(
            "arxiv_id",
            name="uq_papers_arxiv_id",
        ),

        CheckConstraint(
            "year >= 1900 AND year <= 2100",
            name="ck_papers_year_range",
        ),

        Index(
            "ix_papers_year",
            "year",
        ),

        Index(
            "ix_papers_source",
            "source",
        ),
    )


    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )


    authors: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )


    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )


    # Day20：保存去掉 version 后的 canonical arXiv ID。
    arxiv_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )


    url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )


    # Open Access PDF 或 arXiv PDF。
    pdf_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )


    # 原来的 source 表示主要来源。
    # 例如 openalex / arxiv / crossref / manual。
    source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )


    # 论文实际来自哪些 Provider。
    #
    # 示例：
    # ["openalex", "arxiv", "crossref"]
    sources: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )


    # 保存外部数据源 ID。
    #
    # 示例：
    # {
    #     "openalex": "W123",
    #     "arxiv": "1706.03762"
    # }
    external_ids: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'::json"),
    )


    abstract: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )


    keywords: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )


    language: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="en",
    )


    # 期刊 / 会议 / Repository 等来源名称。
    venue: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )


    # 多数据源融合后的引用数。
    # Day19 当前采取 conservative max fusion。
    cited_by_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )


    is_open_access: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
    )


    # --------------------------------------------------------
    # Ownership
    # --------------------------------------------------------

    owner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )


    owner: Mapped[Optional["User"]] = relationship(
        back_populates="papers",
    )


    # --------------------------------------------------------
    # User Saved Papers
    # --------------------------------------------------------

    saved_by_users: Mapped[list["User"]] = relationship(
        secondary=user_saved_papers,
        back_populates="saved_papers",
        lazy="selectin",
    )


    # --------------------------------------------------------
    # Project-Paper Association Object
    # --------------------------------------------------------

    project_links: Mapped[list["ProjectPaper"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
        lazy="selectin",
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

    # --------------------------------------------------------
    # Paper Documents
    # --------------------------------------------------------

    documents: Mapped[
        list["PaperDocument"]
    ] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
        lazy="selectin",
    )