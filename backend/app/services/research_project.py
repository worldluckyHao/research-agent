import logging
from typing import Optional

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import (
    PaperNotFoundException,
    ProjectAccessDeniedException,
    ProjectNotFoundException,
    ProjectPaperAlreadyExistsException,
    ProjectPaperNotFoundException,
)
from backend.app.models.paper import Paper
from backend.app.models.project_paper import ProjectPaper
from backend.app.models.research_project import ResearchProject
from backend.app.schemas.research_project import (
    ResearchProjectCreate,
    ResearchProjectUpdate,
)


logger = logging.getLogger(__name__)


# ============================================================
# Day14：创建 Project
# ============================================================

async def create_project(
    db: AsyncSession,
    project_data: ResearchProjectCreate,
    owner_id: int,
) -> ResearchProject:
    """
    创建属于当前用户的 ResearchProject。
    """

    project = ResearchProject(
        name=project_data.name,
        description=project_data.description,
        owner_id=owner_id,
    )

    try:
        db.add(project)

        await db.commit()
        await db.refresh(project)

        logger.info(
            "Research project created: id=%s owner_id=%s",
            project.id,
            owner_id,
        )

        return project

    except Exception:
        await db.rollback()

        logger.exception(
            "Failed to create research project"
        )

        raise


# ============================================================
# Day14：Project 列表
# ============================================================

async def get_projects(
    db: AsyncSession,
    owner_id: int,
    page: int = 1,
    page_size: int = 20,
):
    """
    分页查询当前用户自己的 Projects。
    """

    count_stmt = (
        select(
            func.count(ResearchProject.id)
        )
        .where(
            ResearchProject.owner_id == owner_id
        )
    )

    total_result = await db.execute(
        count_stmt
    )

    total = total_result.scalar_one()

    pages = (
        (total + page_size - 1) // page_size
        if total > 0
        else 0
    )

    offset = (
        page - 1
    ) * page_size

    stmt = (
        select(ResearchProject)
        .where(
            ResearchProject.owner_id == owner_id
        )
        .order_by(
            ResearchProject.created_at.desc()
        )
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(stmt)

    projects = result.scalars().all()

    return {
        "items": list(projects),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


# ============================================================
# Day14：按 ID 查询
# ============================================================

async def get_project_by_id(
    db: AsyncSession,
    project_id: int,
) -> Optional[ResearchProject]:
    """
    按 Project ID 查询。
    """

    result = await db.execute(
        select(ResearchProject).where(
            ResearchProject.id == project_id
        )
    )

    return result.scalar_one_or_none()


# ============================================================
# Day15：统一 Owner 权限检查
# ============================================================

async def get_owned_project(
    db: AsyncSession,
    project_id: int,
    user_id: int,
) -> ResearchProject:
    """
    查询 Project，并验证当前用户是否为 owner。
    """

    project = await get_project_by_id(
        db=db,
        project_id=project_id,
    )

    if project is None:
        raise ProjectNotFoundException()

    if project.owner_id != user_id:
        raise ProjectAccessDeniedException()

    return project


# ============================================================
# Day14：更新 Project
# ============================================================

async def update_project(
    db: AsyncSession,
    project: ResearchProject,
    project_data: ResearchProjectUpdate,
) -> ResearchProject:
    """
    PATCH 更新 Project。
    """

    update_data = project_data.model_dump(
        exclude_unset=True
    )

    try:
        for field, value in update_data.items():
            setattr(
                project,
                field,
                value,
            )

        await db.commit()
        await db.refresh(project)

        logger.info(
            "Research project updated: id=%s",
            project.id,
        )

        return project

    except Exception:
        await db.rollback()

        logger.exception(
            "Failed to update research project: id=%s",
            project.id,
        )

        raise


# ============================================================
# Day14：删除 Project
# ============================================================

async def delete_project(
    db: AsyncSession,
    project: ResearchProject,
) -> None:
    """
    删除 Project。
    """

    project_id = project.id

    try:
        await db.delete(project)
        await db.commit()

        logger.info(
            "Research project deleted: id=%s",
            project_id,
        )

    except Exception:
        await db.rollback()

        logger.exception(
            "Failed to delete research project: id=%s",
            project_id,
        )

        raise


# ============================================================
# Day15：添加 Paper
# ============================================================

async def add_paper_to_project(
    db: AsyncSession,
    project_id: int,
    paper_id: int,
    user_id: int,
) -> ProjectPaper:
    """
    将 Paper 加入当前用户拥有的 Project。
    """

    # Project 必须存在且属于当前用户。
    await get_owned_project(
        db=db,
        project_id=project_id,
        user_id=user_id,
    )

    # Paper 必须存在。
    paper_result = await db.execute(
        select(Paper).where(
            Paper.id == paper_id
        )
    )

    paper = paper_result.scalar_one_or_none()

    if paper is None:
        raise PaperNotFoundException()

    # 应用层提前检查重复关系。
    existing_result = await db.execute(
        select(ProjectPaper).where(
            ProjectPaper.project_id == project_id,
            ProjectPaper.paper_id == paper_id,
        )
    )

    if existing_result.scalar_one_or_none() is not None:
        raise ProjectPaperAlreadyExistsException()

    link = ProjectPaper(
        project_id=project_id,
        paper_id=paper_id,
    )

    try:
        db.add(link)

        await db.commit()
        await db.refresh(link)

        # 返回接口需要 Paper，因此显式加载 relationship。
        result = await db.execute(
            select(ProjectPaper)
            .where(
                ProjectPaper.project_id == project_id,
                ProjectPaper.paper_id == paper_id,
            )
            .options(
                selectinload(
                    ProjectPaper.paper
                )
            )
        )

        link = result.scalar_one()

        logger.info(
            "Paper added to project: project_id=%s paper_id=%s",
            project_id,
            paper_id,
        )

        return link

    except IntegrityError as exc:
        await db.rollback()

        # 复合主键是数据库层最终防重复机制。
        raise ProjectPaperAlreadyExistsException() from exc

    except Exception:
        await db.rollback()

        logger.exception(
            "Failed to add paper to project"
        )

        raise


# ============================================================
# Day15：Project Papers 分页列表
# ============================================================

async def get_project_papers(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
):
    """
    分页查询 Project 中的 Papers。
    """

    await get_owned_project(
        db=db,
        project_id=project_id,
        user_id=user_id,
    )

    count_result = await db.execute(
        select(
            func.count()
        )
        .select_from(ProjectPaper)
        .where(
            ProjectPaper.project_id == project_id
        )
    )

    total = count_result.scalar_one()

    pages = (
        (total + page_size - 1) // page_size
        if total > 0
        else 0
    )

    offset = (
        page - 1
    ) * page_size

    stmt = (
        select(ProjectPaper)
        .where(
            ProjectPaper.project_id == project_id
        )
        .options(
            # 避免逐条查询 Paper 产生 N+1。
            selectinload(
                ProjectPaper.paper
            )
        )
        .order_by(
            ProjectPaper.added_at.desc()
        )
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(stmt)

    links = result.scalars().all()

    return {
        "items": [
            {
                "paper": link.paper,
                "added_at": link.added_at,
            }
            for link in links
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


# ============================================================
# Day15：移除 Paper
# ============================================================

async def remove_paper_from_project(
    db: AsyncSession,
    project_id: int,
    paper_id: int,
    user_id: int,
) -> None:
    """
    删除 Project-Paper 关联，不删除 Paper 本体。
    """

    await get_owned_project(
        db=db,
        project_id=project_id,
        user_id=user_id,
    )

    result = await db.execute(
        select(ProjectPaper).where(
            ProjectPaper.project_id == project_id,
            ProjectPaper.paper_id == paper_id,
        )
    )

    link = result.scalar_one_or_none()

    if link is None:
        raise ProjectPaperNotFoundException()

    try:
        await db.delete(link)
        await db.commit()

        logger.info(
            "Paper removed from project: project_id=%s paper_id=%s",
            project_id,
            paper_id,
        )

    except Exception:
        await db.rollback()

        logger.exception(
            "Failed to remove paper from project"
        )

        raise