from backend.app.schemas.paper import (
    PaperCreate,
    PaperResponse,
)


PAPERS: dict[int, PaperResponse] = {
    1: PaperResponse(
        id=1,
        title="M3Rain",
        authors=["Author A"],
        year=2026,
        abstract=None,
        keywords=[
            "precipitation",
            "multimodal",
        ],
        language="en",
    ),
    2: PaperResponse(
        id=2,
        title="Rainformer",
        authors=["Author B"],
        year=2024,
        abstract=None,
        keywords=[
            "rainfall",
            "transformer",
        ],
        language="en",
    ),
}


def get_paper_by_id(
    paper_id: int,
) -> PaperResponse | None:

    return PAPERS.get(paper_id)


def create_paper(
    paper: PaperCreate,
) -> PaperResponse:

    new_id = max(
        PAPERS.keys(),
        default=0,
    ) + 1

    new_paper = PaperResponse(
        id=new_id,
        **paper.model_dump(),
    )

    PAPERS[new_id] = new_paper

    return new_paper