# backend/app/services/research_project_service.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.research_project import ResearchProject
from backend.app.schemas.research_project import (
    ResearchProjectCreate,
    ResearchProjectUpdate,
)


async def create_project(
    db: AsyncSession,
    project_in: ResearchProjectCreate,
    owner_id: int,
) -> ResearchProject:
    """
    创建一个研究项目。

    owner_id 必须由当前登录用户提供，
    不能相信前端自己提交 owner_id。
    """

    project = ResearchProject(
        name=project_in.name,
        description=project_in.description,
        owner_id=owner_id,
    )

    db.add(project)

    await db.commit()

    # commit 后刷新对象，
    # 获取数据库生成的 id、created_at 等字段。
    await db.refresh(project)

    return project


async def get_projects_by_owner(
    db: AsyncSession,
    owner_id: int,
) -> list[ResearchProject]:
    """
    查询当前用户拥有的全部研究项目。
    """

    statement = (
        select(ResearchProject)
        .where(
            ResearchProject.owner_id == owner_id
        )
        .order_by(
            ResearchProject.created_at.desc()
        )
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


async def get_project_by_id(
    db: AsyncSession,
    project_id: int,
    owner_id: int,
) -> ResearchProject | None:
    """
    查询指定 ResearchProject。

    注意：
    project_id 和 owner_id 必须同时满足。

    这样才能避免用户通过猜 project_id
    访问其他用户的数据。
    """

    statement = select(ResearchProject).where(
        ResearchProject.id == project_id,
        ResearchProject.owner_id == owner_id,
    )

    result = await db.execute(statement)

    return result.scalar_one_or_none()


async def update_project(
    db: AsyncSession,
    project: ResearchProject,
    project_in: ResearchProjectUpdate,
) -> ResearchProject:
    """
    PATCH 部分更新 ResearchProject。
    """

    # 只获取客户端真正提交的字段。
    update_data = project_in.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return project


async def delete_project(
    db: AsyncSession,
    project: ResearchProject,
) -> None:
    """
    删除研究项目。
    """

    await db.delete(project)

    await db.commit()