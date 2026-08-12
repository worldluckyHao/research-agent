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
        max_length=200
    )

    authors: list[str] = Field(
        min_length=1
    )

    year: int = Field(
        ge=1900,
        le=2100
    )

    abstract: str | None = Field(
        default=None,
        max_length=5000
    )

    keywords: list[str] = Field(
        default_factory=list,
        max_length=10
    )

    language: str = "en"


class PaperResponse(BaseModel):
    id: int

    title: str

    authors: list[str]

    year: int

    abstract: str | None = None

    keywords: list[str] = Field(
        default_factory=list
    )

    language: str = "en"