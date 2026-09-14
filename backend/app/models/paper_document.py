from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    Text,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from backend.app.db.base import Base


class PaperDocument(Base):
    """
    Paper 对应的全文文档。

    Day23 保存文件 Metadata。

    Day24 会使用 status 字段
    跟踪 PDF Parsing 状态。
    """

    __tablename__ = "paper_documents"


    __table_args__ = (

        # 同一篇 Paper 不重复保存完全相同的 PDF。
        UniqueConstraint(
            "paper_id",
            "sha256",
            name=(
                "uq_paper_documents_"
                "paper_sha256"
            ),
        ),

        CheckConstraint(
            (
                "status IN "
                "('uploaded', "
                "'queued', "
                "'parsing', "
                "'parsed', "
                "'failed')"
            ),
            name=(
                "ck_paper_documents_"
                "status"
            ),
        ),

        Index(
            "ix_paper_documents_"
            "paper_created",
            "paper_id",
            "created_at",
        ),
    )


    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    paper_id: Mapped[int] = mapped_column(
        ForeignKey(
            "papers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    uploaded_by_id: Mapped[
        Optional[int]
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )


    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


    storage_backend: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )


    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )


    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/pdf",
    )


    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )


    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )


    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploaded",
        server_default="uploaded",
        index=True,
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


    paper: Mapped["Paper"] = relationship(
        back_populates="documents",
    )

    pages: Mapped[
        list["PaperDocumentPage"]
    ] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by=(
            "PaperDocumentPage.page_number"
        ),
    )

    # --------------------------------------------------------
    # PDF Parsing Metadata
    # --------------------------------------------------------

    page_count: Mapped[
        Optional[int]
    ] = mapped_column(
        Integer,
        nullable=True,
    )


    parser_name: Mapped[
        Optional[str]
    ] = mapped_column(
        String(50),
        nullable=True,
    )


    parser_version: Mapped[
        Optional[str]
    ] = mapped_column(
        String(50),
        nullable=True,
    )


    parse_error: Mapped[
        Optional[str]
    ] = mapped_column(
        Text,
        nullable=True,
    )


    parsed_at: Mapped[
        Optional[datetime]
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )