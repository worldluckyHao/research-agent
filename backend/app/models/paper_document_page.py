from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.app.db.base import Base


class PaperDocumentPage(Base):
    """
    PDF 单页解析结果。

    一个 PaperDocument 对应多个 Page。

    Day25 Chunking 会直接基于这些 Page Text。
    """

    __tablename__ = "paper_document_pages"


    __table_args__ = (

        # 同一个 Document 中，
        # page_number 必须唯一。
        UniqueConstraint(
            "document_id",
            "page_number",
            name=(
                "uq_document_pages_"
                "document_page"
            ),
        ),

        Index(
            "ix_document_pages_"
            "document_page",
            "document_id",
            "page_number",
        ),
    )


    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "paper_documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    # PDF 页码从 1 开始。
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    # 当前页面提取的正文。
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )


    # 方便后续分析文本长度，
    # 避免每次重新 len(text)。
    char_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )


    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )


    document: Mapped[
        "PaperDocument"
    ] = relationship(
        back_populates="pages",
    )