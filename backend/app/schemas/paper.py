from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class PaperCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    title: str = Field(
        min_length=3,
        max_length=200,
    )

    authors: list[str] = Field(
        min_length=1,
    )

    year: int = Field(
        ge=1900,
        le=2100,
    )

    doi: Optional[str] = Field(
        default=None,
        max_length=255,
    )

    abstract: Optional[str] = Field(
        default=None,
        max_length=5000,
    )

    keywords: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    language: str = "en"


class PaperUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    authors: Optional[list[str]] = Field(
        default=None,
        min_length=1,
    )

    year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
    )

    doi: Optional[str] = Field(
        default=None,
        max_length=255,
    )

    abstract: Optional[str] = Field(
        default=None,
        max_length=5000,
    )

    keywords: Optional[list[str]] = Field(
        default=None,
        max_length=10,
    )

    language: Optional[str] = None


class PaperResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    title: str

    authors: list[str]

    year: int

    doi: Optional[str] = None

    abstract: Optional[str] = None

    keywords: list[str] = Field(
        default_factory=list
    )

    language: str = "en"

    created_at: datetime