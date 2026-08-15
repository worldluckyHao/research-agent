from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

