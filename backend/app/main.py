from fastapi import FastAPI, status

from backend.app.schemas.paper import (
    PaperCreate,
    PaperResponse,
)


app = FastAPI(
    title="ResearchAgent API",
    version="0.2.0"
)


@app.get("/")
def root():
    return {
        "message": "ResearchAgent API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "research-agent"
    }


@app.get("/papers/{paper_id}")
def get_paper(
    paper_id: int
):
    return {
        "paper_id": paper_id
    }


@app.get("/papers")
def search_papers(
    keyword: str | None = None,
    page: int = 1
):
    return {
        "keyword": keyword,
        "page": page
    }


@app.post(
    "/papers",
    response_model=PaperResponse,
    status_code=status.HTTP_201_CREATED
)
def create_paper(
    paper: PaperCreate
):
    return {
        "id": 1001,
        **paper.model_dump(),
        "internal_note": "not exposed"
    }