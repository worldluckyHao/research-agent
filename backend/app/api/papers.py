from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.schemas.paper import (
    PaperCreate,
    PaperResponse,
    PaperUpdate,
)
from backend.app.services import paper_service


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
    response_model=List[PaperResponse],
)
async def get_papers(
    db: AsyncSession = Depends(get_db),
):
    return await paper_service.get_papers(db)


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