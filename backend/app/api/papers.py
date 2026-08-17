from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.schemas.paper import (
    PaperCreate,
    PaperListResponse,
    PaperResponse,
    PaperUpdate,
)
from backend.app.services import paper_service
from typing import Literal, Optional

router = APIRouter(
    prefix="/papers",
    tags=["papers"],
)


@router.post(
    "/",
    response_model=PaperResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_paper(
    paper_data: PaperCreate,
    db: AsyncSession = Depends(get_db),
):
    return await paper_service.create_paper(
        db=db,
        paper_data=paper_data,
    )


@router.get(
    "/",
    response_model=PaperListResponse,
)
async def get_papers(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    year: Optional[int] = Query(
        default=None,
        ge=1900,
        le=2100,
    ),
    source: Optional[str] = Query(
        default=None,
        max_length=100,
    ),
    search: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=200,
    ),
    sort_by: Literal[
        "id",
        "title",
        "year",
        "created_at",
        "updated_at",
    ] = "id",
    sort_order: Literal[
        "asc",
        "desc",
    ] = "asc",
    db: AsyncSession = Depends(get_db),
):
    return await paper_service.get_papers(
        db=db,
        page=page,
        page_size=page_size,
        year=year,
        source=source,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{paper_id}",
    response_model=PaperResponse,
)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
    )

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    return paper


@router.patch(
    "/{paper_id}",
    response_model=PaperResponse,
)
async def update_paper(
    paper_id: int,
    paper_data: PaperUpdate,
    db: AsyncSession = Depends(get_db),
):
    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
    )

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    return await paper_service.update_paper(
        db=db,
        paper=paper,
        paper_data=paper_data,
    )


@router.delete(
    "/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
    )

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    await paper_service.delete_paper(
        db=db,
        paper=paper,
    )