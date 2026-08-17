from typing import Literal, Optional

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    EmptyUpdateException,
    PaperNotFoundException,
)
from backend.app.dependencies import get_db
from backend.app.schemas.paper import (
    PaperCreate,
    PaperListResponse,
    PaperResponse,
    PaperUpdate,
)
from backend.app.services import paper_service


# ============================================================
# Paper Router
# ============================================================

router = APIRouter(
    prefix="/papers",
    tags=["papers"],
)


# ============================================================
# 创建 Paper
# ============================================================

@router.post(
    "/",
    response_model=PaperResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_paper(
    paper_data: PaperCreate,

    # FastAPI 会自动调用 get_db()，
    # 得到一个 AsyncSession。
    db: AsyncSession = Depends(get_db),
):
    """
    创建一篇新的 Paper。

    Request Body 经过：

        PaperCreate

    做 Pydantic 校验。

    真正保存数据库的逻辑交给：

        paper_service.create_paper()
    """

    return await paper_service.create_paper(
        db=db,
        paper_data=paper_data,
    )


# ============================================================
# 查询 Paper 列表
# ============================================================

@router.get(
    "/",
    response_model=PaperListResponse,
)
async def get_papers(
    # ========================================================
    # Pagination
    # ========================================================

    page: int = Query(
        default=1,
        ge=1,
        description="Current page number",
    ),

    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of papers per page",
    ),

    # ========================================================
    # Filters
    # ========================================================

    year: Optional[int] = Query(
        default=None,
        ge=1900,
        le=2100,
        description="Filter papers by publication year",
    ),

    source: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Filter papers by source",
    ),

    # ========================================================
    # Search
    # ========================================================

    search: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Search in paper title and abstract",
    ),

    # ========================================================
    # Sorting
    # ========================================================

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
    """
    查询 Paper 列表。

    支持：

    - 分页
    - year 过滤
    - source 过滤
    - title / abstract 模糊搜索
    - 排序

    例如：

    /papers/?page=1&page_size=10

    /papers/?year=2025

    /papers/?source=arXiv

    /papers/?search=transformer

    /papers/?sort_by=year&sort_order=desc
    """

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


# ============================================================
# 根据 ID 查询单篇 Paper
# ============================================================

@router.get(
    "/{paper_id}",
    response_model=PaperResponse,
)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    根据 Paper ID 查询论文。

    如果数据库不存在该 Paper：

        raise PaperNotFoundException()

    最后由统一异常 Handler 转成：

        HTTP 404
    """

    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
    )

    if paper is None:
        raise PaperNotFoundException()

    return paper


# ============================================================
# PATCH 修改 Paper
# ============================================================

@router.patch(
    "/{paper_id}",
    response_model=PaperResponse,
)
async def update_paper(
    paper_id: int,
    paper_data: PaperUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    部分更新 Paper。

    PATCH 的特点：

    客户端只需要提交真正想修改的字段。

    例如：

    {
        "year": 2025
    }

    不需要重新提交完整 Paper。
    """

    # ========================================================
    # 防止空 PATCH
    # ========================================================
    #
    # 如果客户端：
    #
    # {}
    #
    # 什么字段都没有提交，
    # 就直接返回 400。
    #
    if not paper_data.model_fields_set:
        raise EmptyUpdateException()

    # ========================================================
    # 先查询 Paper
    # ========================================================

    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
    )

    # Paper 不存在：
    #
    # HTTP 404
    if paper is None:
        raise PaperNotFoundException()

    # ========================================================
    # 真正执行更新
    # ========================================================

    return await paper_service.update_paper(
        db=db,
        paper=paper,
        paper_data=paper_data,
    )


# ============================================================
# 删除 Paper
# ============================================================

@router.delete(
    "/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除 Paper。

    成功：

        HTTP 204 No Content

    Paper 不存在：

        HTTP 404
    """

    # 先查询 Paper。
    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
    )

    if paper is None:
        raise PaperNotFoundException()

    # 删除数据库记录。
    await paper_service.delete_paper(
        db=db,
        paper=paper,
    )