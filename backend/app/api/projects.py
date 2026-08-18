from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    EmptyUpdateException,
    ProjectNotFoundException,
)
from backend.app.dependencies import (
    get_current_user,
    get_db,
)
from backend.app.models.user import User
from backend.app.schemas.research_project import (
    ResearchProjectCreate,
    ResearchProjectResponse,
    ResearchProjectUpdate,
)
from backend.app.services import (
    research_project as research_project_service,
)


# ============================================================
# Research Project Router
# ============================================================

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


# ============================================================
# 创建 Research Project
# ============================================================

@router.post(
    "/",
    response_model=ResearchProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    project_data: ResearchProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建当前登录用户自己的研究项目。

    owner_id 不允许客户端提交，
    统一从 JWT 对应的 current_user 获取。
    """

    return await research_project_service.create_project(
        db=db,
        project_in=project_data,
        owner_id=current_user.id,
    )


# ============================================================
# 查询当前用户所有 Research Projects
# ============================================================

@router.get(
    "/",
    response_model=list[ResearchProjectResponse],
)
async def get_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询当前登录用户自己的全部研究项目。
    """

    return await research_project_service.get_projects_by_owner(
        db=db,
        owner_id=current_user.id,
    )


# ============================================================
# 根据 ID 查询 Project
# ============================================================

@router.get(
    "/{project_id}",
    response_model=ResearchProjectResponse,
)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    查询当前用户自己的指定 Project。

    查询条件不仅包含 project_id，
    还包含 owner_id。
    """

    project = await research_project_service.get_project_by_id(
        db=db,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if project is None:
        raise ProjectNotFoundException()

    return project


# ============================================================
# PATCH 修改 Project
# ============================================================

@router.patch(
    "/{project_id}",
    response_model=ResearchProjectResponse,
)
async def update_project(
    project_id: int,
    project_data: ResearchProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    部分更新当前用户自己的 Research Project。
    """

    # --------------------------------------------------------
    # 防止空 PATCH：
    #
    # {}
    # --------------------------------------------------------
    if not project_data.model_fields_set:
        raise EmptyUpdateException()

    # --------------------------------------------------------
    # 查询 Project，同时验证 owner
    # --------------------------------------------------------
    project = await research_project_service.get_project_by_id(
        db=db,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if project is None:
        raise ProjectNotFoundException()

    # --------------------------------------------------------
    # 真正执行更新
    # --------------------------------------------------------
    return await research_project_service.update_project(
        db=db,
        project=project,
        project_in=project_data,
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
    current_user: User = Depends(get_current_user),
):
    """
    删除当前用户自己的 Research Project。
    """

    project = await research_project_service.get_project_by_id(
        db=db,
        project_id=project_id,
        owner_id=current_user.id,
    )

    if project is None:
        raise ProjectNotFoundException()

    await research_project_service.delete_project(
        db=db,
        project=project,
    )