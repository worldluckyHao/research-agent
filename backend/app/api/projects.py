from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    EmptyUpdateException,
)
from backend.app.dependencies import (
    get_current_user,
    get_db,
)
from backend.app.models.user import User
from backend.app.schemas.research_project import (
    ProjectPaperListResponse,
    ProjectPaperResponse,
    ResearchProjectCreate,
    ResearchProjectListResponse,
    ResearchProjectResponse,
    ResearchProjectUpdate,
)
from backend.app.services import (
    research_project as project_service,
)


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


# ============================================================
# 创建 Project
# ============================================================

@router.post(
    "/",
    response_model=ResearchProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    project_data: ResearchProjectCreate,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    创建当前用户自己的 ResearchProject。
    """

    return await project_service.create_project(
        db=db,
        project_data=project_data,
        owner_id=current_user.id,
    )


# ============================================================
# Project 列表
# ============================================================

@router.get(
    "/",
    response_model=ResearchProjectListResponse,
)
async def get_projects(
    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    查询当前用户自己的 Projects。
    """

    return await project_service.get_projects(
        db=db,
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
    )


# ============================================================
# 查询单个 Project
# ============================================================

@router.get(
    "/{project_id}",
    response_model=ResearchProjectResponse,
)
async def get_project(
    project_id: int,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    查询 Project，同时进行 owner 权限校验。
    """

    return await project_service.get_owned_project(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
    )


# ============================================================
# 更新 Project
# ============================================================

@router.patch(
    "/{project_id}",
    response_model=ResearchProjectResponse,
)
async def update_project(
    project_id: int,
    project_data: ResearchProjectUpdate,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    更新当前用户自己的 Project。
    """

    if not project_data.model_fields_set:
        raise EmptyUpdateException()

    project = await project_service.get_owned_project(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
    )

    return await project_service.update_project(
        db=db,
        project=project,
        project_data=project_data,
    )


# ============================================================
# 删除 Project
# ============================================================

@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: int,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    删除当前用户自己的 Project。
    """

    project = await project_service.get_owned_project(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
    )

    await project_service.delete_project(
        db=db,
        project=project,
    )


# ============================================================
# Day15：添加 Paper 到 Project
# ============================================================

@router.post(
    "/{project_id}/papers/{paper_id}",
    response_model=ProjectPaperResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_paper_to_project(
    project_id: int,
    paper_id: int,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    将 Paper 加入当前用户拥有的 Project。
    """

    link = await project_service.add_paper_to_project(
        db=db,
        project_id=project_id,
        paper_id=paper_id,
        user_id=current_user.id,
    )

    return {
        "paper": link.paper,
        "added_at": link.added_at,
    }


# ============================================================
# Day15：查询 Project Papers
# ============================================================

@router.get(
    "/{project_id}/papers",
    response_model=ProjectPaperListResponse,
)
async def get_project_papers(
    project_id: int,

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    分页查询 Project 中的 Papers。
    """

    return await project_service.get_project_papers(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


# ============================================================
# Day15：从 Project 移除 Paper
# ============================================================

@router.delete(
    "/{project_id}/papers/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_paper_from_project(
    project_id: int,
    paper_id: int,

    db: AsyncSession = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    只删除 Project-Paper 关系，不删除 Paper 本身。
    """

    await project_service.remove_paper_from_project(
        db=db,
        project_id=project_id,
        paper_id=paper_id,
        user_id=current_user.id,
    )