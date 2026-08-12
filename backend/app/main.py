# -*- coding: utf-8 -*-
# @ Time：2026/8/11 14:21
# @ Auth：zh
# @ File：main.py
# @Company：HUT
from fastapi import FastAPI
from pydantic import BaseModel


class PaperCreate(BaseModel):
    title: str
    authors: list[str]
    year: int


app = FastAPI()


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
def get_paper(paper_id: int):
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

@app.post("/papers")
def create_paper(paper: PaperCreate):
    return {
        "message": "paper created",
        "paper": paper
    }