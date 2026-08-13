from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from backend.app.dependencies import (
    get_current_user,
)

from backend.app.schemas.paper import (
    PaperCreate,
    PaperResponse,
)

from backend.app.services import (
    paper_service,
)


router = APIRouter(
    prefix="/papers",
    tags=["papers"],
)


@router.get("/")
def search_papers(
    keyword: str | None = None,
    page: int = 1,
):
    return {
        "keyword": keyword,
        "page": page,
    }


@router.get(
    "/{paper_id}",
    response_model=PaperResponse,
)
def get_paper(
    paper_id: int,
):

    paper = paper_service.get_paper_by_id(
        paper_id
    )

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    return paper


@router.post(
    "/",
    response_model=PaperResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_paper(
    paper: PaperCreate,
    current_user: dict = Depends(
        get_current_user
    ),
):

    print(
        "Current user:",
        current_user
    )

    return paper_service.create_paper(
        paper
    )