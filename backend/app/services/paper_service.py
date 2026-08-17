from typing import Optional

from sqlalchemy import (
    asc,
    desc,
    func,
    or_,
    select,
)
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
        url=paper_data.url,
        source=paper_data.source,
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
    page: int = 1,
    page_size: int = 20,
    year: Optional[int] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
):
    filters = []

    if year is not None:
        filters.append(
            Paper.year == year
        )

    if source is not None:
        filters.append(
            Paper.source == source
        )

    if search:
        search_pattern = f"%{search}%"

        filters.append(
            or_(
                Paper.title.ilike(
                    search_pattern
                ),
                Paper.abstract.ilike(
                    search_pattern
                ),
            )
        )

    count_stmt = (
        select(func.count(Paper.id))
        .where(*filters)
    )

    total_result = await db.execute(
        count_stmt
    )

    total = total_result.scalar_one()

    pages = (
        (total + page_size - 1)
        // page_size
        if total > 0
        else 0
    )

    offset = (
        page - 1
    ) * page_size

    sort_columns = {
        "id": Paper.id,
        "title": Paper.title,
        "year": Paper.year,
        "created_at": Paper.created_at,
        "updated_at": Paper.updated_at,
    }

    sort_column = sort_columns.get(
        sort_by,
        Paper.id,
    )

    if sort_order == "desc":
        ordering = desc(sort_column)
    else:
        ordering = asc(sort_column)

    stmt = (
        select(Paper)
        .where(*filters)
        .order_by(ordering)
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(stmt)

    papers = result.scalars().all()

    return {
        "items": list(papers),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


async def get_paper_by_id(
    db: AsyncSession,
    paper_id: int,
) -> Optional[Paper]:
    result = await db.execute(
        select(Paper).where(
            Paper.id == paper_id
        )
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