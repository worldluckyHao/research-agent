from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.paper import Paper
from backend.app.schemas.paper import (
    PaperCreate,
    PaperUpdate,
)


async def create_paper(
    db: AsyncSession,
    paper_data: PaperCreate,
) -> Paper:

    paper = Paper(
        title=paper_data.title,
        authors=paper_data.authors,
        year=paper_data.year,
        doi=paper_data.doi,
        abstract=paper_data.abstract,
        keywords=paper_data.keywords,
        language=paper_data.language,
    )

    try:
        db.add(paper)

        await db.commit()

        await db.refresh(paper)

        return paper

    except Exception:
        await db.rollback()
        raise


async def get_papers(
    db: AsyncSession,
) -> List[Paper]:

    result = await db.execute(
        select(Paper).order_by(Paper.id)
    )

    papers = result.scalars().all()

    return list(papers)


async def get_paper_by_id(
    db: AsyncSession,
    paper_id: int,
) -> Optional[Paper]:

    result = await db.execute(
        select(Paper).where(Paper.id == paper_id)
    )

    return result.scalar_one_or_none()


async def update_paper(
    db: AsyncSession,
    paper: Paper,
    paper_data: PaperUpdate,
) -> Paper:

    update_data = paper_data.model_dump(
        exclude_unset=True
    )

    try:
        for field, value in update_data.items():
            setattr(
                paper,
                field,
                value,
            )

        await db.commit()

        await db.refresh(paper)

        return paper

    except Exception:
        await db.rollback()
        raise


async def delete_paper(
    db: AsyncSession,
    paper: Paper,
) -> None:

    try:
        await db.delete(paper)

        await db.commit()

    except Exception:
        await db.rollback()
        raise