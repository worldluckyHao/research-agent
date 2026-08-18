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
from backend.app.dependencies import (
    get_current_user,
    get_db,
)
from backend.app.models.user import User
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

    db: AsyncSession = Depends(get_db),

    # ========================================================
    # 当前登录用户
    # ========================================================
    #
    # 创建 Paper 必须登录。
    #
    # current_user 来自 JWT：
    #
    # Authorization: Bearer <token>
    #
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    创建论文。

    owner_id 自动取当前登录用户，
    客户端不能自己指定。

    例如：

        current_user.id = 1

    最终：

        paper.owner_id = 1
    """

    return await paper_service.create_paper(
        db=db,
        paper_data=paper_data,

        # ====================================================
        # Paper 的 Owner 来自当前登录用户
        # ====================================================
        owner_id=current_user.id,
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

    # ========================================================
    # Database Session
    # ========================================================

    db: AsyncSession = Depends(get_db),

    # ========================================================
    # Day14：当前登录用户
    # ========================================================
    #
    # GET /papers/
    #
    # 现在不再是公开查询全部 Paper，
    # 而是只查询当前用户自己的 Paper。
    #
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    查询当前登录用户自己的 Paper 列表。

    支持：

    - 用户级数据隔离
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

        # ====================================================
        # Day14：Ownership Filter
        # ====================================================
        #
        # Service 中会使用：
        #
        # Paper.owner_id == owner_id
        #
        # 所以这里只会返回当前用户自己的论文。
        #
        owner_id=current_user.id,

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

    # ========================================================
    # Day14：查询单篇 Paper 也必须登录
    # ========================================================
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    根据 Paper ID 查询当前用户自己的论文。

    查询时不仅检查：

        Paper.id == paper_id

    还检查：

        Paper.owner_id == current_user.id

    因此即使用户猜到了其他人的 paper_id，
    也不能读取对应论文。
    """

    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,

        # ====================================================
        # Object-Level Authorization
        # ====================================================
        owner_id=current_user.id,
    )

    # ========================================================
    # Paper 不存在 OR 不属于当前用户
    # ========================================================
    #
    # 两种情况统一返回：
    #
    # HTTP 404
    #
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

    # ========================================================
    # Day14：修改 Paper 必须登录
    # ========================================================
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    部分更新当前用户自己的 Paper。

    PATCH 的特点：

    客户端只需要提交真正想修改的字段。

    例如：

    {
        "year": 2025
    }

    不需要重新提交完整 Paper。
    """

    # ========================================================
    # 1. 防止空 PATCH
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
    # 2. 查询当前用户自己的 Paper
    # ========================================================
    #
    # 注意：
    #
    # 这里不是单纯：
    #
    # Paper.id == paper_id
    #
    # 而是：
    #
    # Paper.id == paper_id
    #
    # AND
    #
    # Paper.owner_id == current_user.id
    #
    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
        owner_id=current_user.id,
    )

    # ========================================================
    # Paper 不存在 OR 不属于当前用户
    # ========================================================

    if paper is None:
        raise PaperNotFoundException()

    # ========================================================
    # 3. 真正执行更新
    # ========================================================
    #
    # 到这里的 paper 已经通过 ownership check。
    #
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

    # ========================================================
    # Day14：删除 Paper 必须登录
    # ========================================================
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    删除当前用户自己的 Paper。

    成功：

        HTTP 204 No Content

    Paper 不存在：

        HTTP 404

    Paper 存在但属于其他用户：

        仍然 HTTP 404
    """

    # ========================================================
    # 1. 查询当前用户自己的 Paper
    # ========================================================

    paper = await paper_service.get_paper_by_id(
        db=db,
        paper_id=paper_id,
        owner_id=current_user.id,
    )

    # ========================================================
    # Paper 不存在 OR 越权访问
    # ========================================================

    if paper is None:
        raise PaperNotFoundException()

    # ========================================================
    # 2. 删除数据库记录
    # ========================================================

    await paper_service.delete_paper(
        db=db,
        paper=paper,
    )