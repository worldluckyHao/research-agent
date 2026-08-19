# backend/app/services/paper_service.py

import logging
from typing import Optional

from sqlalchemy import (
    asc,
    desc,
    func,
    or_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    PaperDOIExistsException,
)
from backend.app.models.paper import Paper
from backend.app.schemas.paper import (
    PaperCreate,
    PaperUpdate,
)
from sqlalchemy.orm import selectinload
from backend.app.core.exceptions import (
    ProjectAccessDeniedException,
    ProjectNotFoundException,
    ProjectPaperAlreadyExistsException,
    ProjectPaperNotFoundException,
)
from backend.app.models.paper import Paper
from backend.app.models.project_paper import ProjectPaper
from backend.app.models.research_project import ResearchProject

# ============================================================
# 当前 Service 模块 logger
# ============================================================
#
# __name__ 会得到当前模块名称：
#
# backend.app.services.paper_service
#
# 日志里就可以知道是哪一个模块产生的记录。
#
logger = logging.getLogger(__name__)


# ============================================================
# 创建 Paper
# ============================================================

async def create_paper(
    db: AsyncSession,
    paper_data: PaperCreate,
    owner_id: int,
) -> Paper:
    """
    创建 Paper，并记录创建者。

    owner_id 不允许由客户端自己指定，
    而是由 Router 从 current_user.id 中取得。
    """

    paper = Paper(
        title=paper_data.title,
        authors=paper_data.authors,
        year=paper_data.year,
        doi=paper_data.doi,
        url=paper_data.url,
        source=paper_data.source,
        abstract=paper_data.abstract,
        keywords=paper_data.keywords,
        language=paper_data.language,

        # ====================================================
        # Day13 / Day14：绑定 Paper Owner
        # ====================================================
        #
        # 例如：
        #
        # 当前登录用户：
        #
        # current_user.id = 1
        #
        # 创建后：
        #
        # paper.owner_id = 1
        #
        owner_id=owner_id,
    )

    try:
        # ----------------------------------------------------
        # 把 ORM 对象加入当前数据库 Session
        # ----------------------------------------------------
        db.add(paper)

        # ----------------------------------------------------
        # 提交事务
        # ----------------------------------------------------
        await db.commit()

        # ----------------------------------------------------
        # 刷新 ORM 对象
        #
        # 得到数据库生成的：
        #
        # id
        # created_at
        # updated_at
        # 等字段
        # ----------------------------------------------------
        await db.refresh(paper)

        logger.info(
            "Paper created: id=%s owner_id=%s",
            paper.id,
            owner_id,
        )

        return paper

    # ========================================================
    # 数据库完整性异常
    # ========================================================
    #
    # 主要处理 DOI UNIQUE 冲突。
    #
    except IntegrityError as exc:
        await db.rollback()

        if (
            paper_data.doi is not None
            and "uq_papers_doi" in str(exc.orig)
        ):
            logger.warning(
                "Duplicate paper DOI: %s",
                paper_data.doi,
            )

            raise PaperDOIExistsException() from exc

        logger.exception(
            "Database integrity error while creating paper"
        )

        raise

    # ========================================================
    # 未知异常
    # ========================================================

    except Exception:
        await db.rollback()

        logger.exception(
            "Unexpected error while creating paper"
        )

        raise

async def get_owned_project(
    db: AsyncSession,
    project_id: int,
    user_id: int,
) -> ResearchProject:
    """
    查询 Project，并验证当前用户是否为 owner。
    """

    result = await db.execute(
        select(ResearchProject).where(
            ResearchProject.id == project_id
        )
    )

    project = result.scalar_one_or_none()

    if project is None:
        raise ProjectNotFoundException()

    if project.owner_id != user_id:
        raise ProjectAccessDeniedException()

    return project

# ============================================================
# 查询 Paper 列表
# ============================================================

async def get_papers(
    db: AsyncSession,

    # ========================================================
    # Day14：当前用户 ID
    # ========================================================
    #
    # 这是整个列表权限隔离的关键参数。
    #
    owner_id: int,

    page: int = 1,
    page_size: int = 20,
    year: Optional[int] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
):
    """
    查询当前用户自己的 Paper 列表。

    支持：

    1. Ownership Authorization
    2. Pagination
    3. Filter
    4. Search
    5. Sorting

    最重要的规则：

        Paper.owner_id == owner_id

    因此不同用户之间的数据互相隔离。
    """

    # ========================================================
    # 动态过滤条件
    # ========================================================

    filters = []

    # ========================================================
    # Day14：Ownership Filter
    # ========================================================
    #
    # 这是整个 Paper 列表权限控制最重要的一行。
    #
    # 假设：
    #
    # owner_id = 1
    #
    # 最终 SQL 中会包含：
    #
    # WHERE papers.owner_id = 1
    #
    # 所以 User 1 只能看到自己的 Paper。
    #
    filters.append(
        Paper.owner_id == owner_id
    )

    # ========================================================
    # year 过滤
    # ========================================================
    #
    # 如果客户端：
    #
    # GET /papers/?year=2025
    #
    # SQL 会进一步增加：
    #
    # AND papers.year = 2025
    #
    if year is not None:
        filters.append(
            Paper.year == year
        )

    # ========================================================
    # source 过滤
    # ========================================================
    #
    # 例如：
    #
    # GET /papers/?source=arXiv
    #
    if source is not None:
        filters.append(
            Paper.source == source
        )

    # ========================================================
    # title + abstract 模糊搜索
    # ========================================================

    if search:
        # ----------------------------------------------------
        # 例如：
        #
        # search = transformer
        #
        # 转成：
        #
        # %transformer%
        #
        # PostgreSQL ILIKE：
        #
        # 不区分大小写模糊匹配
        # ----------------------------------------------------
        search_pattern = f"%{search}%"

        filters.append(
            or_(
                # title ILIKE '%transformer%'
                Paper.title.ilike(
                    search_pattern
                ),

                # abstract ILIKE '%transformer%'
                Paper.abstract.ilike(
                    search_pattern
                ),
            )
        )

    # ========================================================
    # 查询符合条件的总数量
    # ========================================================
    #
    # 这里特别重要。
    #
    # count 查询必须使用和正式列表查询
    # 完全一致的 filters。
    #
    # 因为 filters 中现在已经包含：
    #
    # Paper.owner_id == owner_id
    #
    # 所以 total 只统计当前用户的数据。
    #
    count_stmt = (
        select(
            func.count(Paper.id)
        )
        .where(*filters)
    )

    total_result = await db.execute(
        count_stmt
    )

    # COUNT 查询只返回一个数字。
    total = total_result.scalar_one()

    # ========================================================
    # 计算总页数
    # ========================================================
    #
    # 例如：
    #
    # total = 41
    # page_size = 20
    #
    # pages = 3
    #
    if total > 0:
        pages = (
            total + page_size - 1
        ) // page_size
    else:
        pages = 0

    # ========================================================
    # 计算 OFFSET
    # ========================================================
    #
    # page = 1:
    #
    # offset = 0
    #
    # page = 2:
    #
    # offset = page_size
    #
    offset = (
        page - 1
    ) * page_size

    # ========================================================
    # 排序字段白名单
    # ========================================================
    #
    # 客户端不能直接告诉数据库：
    #
    # "我要按照任意 ORM 属性排序"
    #
    # 而只能从下面这些字段里选。
    #
    # Router 层已经通过 Literal 做第一层校验，
    # Service 层这里再做一次白名单兜底。
    #
    sort_columns = {
        "id": Paper.id,
        "title": Paper.title,
        "year": Paper.year,
        "created_at": Paper.created_at,
        "updated_at": Paper.updated_at,
    }

    sort_column = sort_columns.get(
        sort_by,
        Paper.id,
    )

    # ========================================================
    # ASC / DESC
    # ========================================================

    if sort_order == "desc":
        ordering = desc(
            sort_column
        )
    else:
        ordering = asc(
            sort_column
        )

    # ========================================================
    # 构造最终查询
    # ========================================================
    #
    # 最终大概会形成：
    #
    # SELECT *
    # FROM papers
    # WHERE
    #     owner_id = ?
    #     AND year = ?
    #     AND ...
    # ORDER BY ...
    # OFFSET ...
    # LIMIT ...
    #
    stmt = (
        select(Paper)

        # ----------------------------------------------------
        # Ownership + Filters + Search
        # ----------------------------------------------------
        .where(*filters)

        # ----------------------------------------------------
        # ORDER BY
        # ----------------------------------------------------
        .order_by(ordering)

        # ----------------------------------------------------
        # Pagination
        # ----------------------------------------------------
        .offset(offset)
        .limit(page_size)
    )

    # ========================================================
    # 执行 SQL
    # ========================================================

    result = await db.execute(
        stmt
    )

    # --------------------------------------------------------
    # scalars()
    #
    # 从 SQLAlchemy Result 中提取 Paper ORM 对象。
    # --------------------------------------------------------
    papers = result.scalars().all()

    # ========================================================
    # 返回统一分页结构
    # ========================================================

    return {
        "items": list(papers),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


# ============================================================
# 根据 ID 查询 Paper
# ============================================================

async def get_paper_by_id(
    db: AsyncSession,
    paper_id: int,
    owner_id: int,
) -> Paper | None:
    """
    根据 Paper ID 查询当前用户拥有的论文。

    查询必须同时满足：

    1. Paper.id == paper_id
    2. Paper.owner_id == owner_id

    这样可以防止用户通过猜测 paper_id
    读取其他用户的 Paper。
    """

    # ========================================================
    # Object-Level Authorization
    # ========================================================
    #
    # 原来如果只有：
    #
    # Paper.id == paper_id
    #
    # 那么只要知道其他用户的 paper_id，
    # 就有可能读取他的论文。
    #
    # 现在：
    #
    # Paper.id == paper_id
    # AND
    # Paper.owner_id == owner_id
    #
    # 两个条件必须同时成立。
    #
    statement = select(Paper).where(
        Paper.id == paper_id,
        Paper.owner_id == owner_id,
    )

    result = await db.execute(
        statement
    )

    # 如果：
    #
    # Paper 不存在
    #
    # 或者：
    #
    # Paper 存在，但属于其他用户
    #
    # 都会返回 None。
    #
    return result.scalar_one_or_none()


# ============================================================
# 更新 Paper
# ============================================================

async def update_paper(
    db: AsyncSession,
    paper: Paper,
    paper_data: PaperUpdate,
) -> Paper:
    """
    PATCH 更新 Paper。

    注意：

    进入这个函数之前，
    Router 已经通过 get_paper_by_id()
    完成了 Ownership Check。

    所以这里拿到的是一个已经授权的 Paper ORM 对象。
    """

    # ========================================================
    # exclude_unset=True
    # ========================================================
    #
    # 假设客户端只发送：
    #
    # {
    #     "year": 2025
    # }
    #
    # 那么 update_data：
    #
    # {
    #     "year": 2025
    # }
    #
    # 没有发送的字段不会被覆盖。
    #
    update_data = paper_data.model_dump(
        exclude_unset=True
    )

    try:
        # ====================================================
        # 动态更新 ORM 属性
        # ====================================================

        for field, value in update_data.items():
            # 例如：
            #
            # field = "year"
            # value = 2025
            #
            # 等价于：
            #
            # paper.year = 2025
            #
            setattr(
                paper,
                field,
                value,
            )

        # ----------------------------------------------------
        # 提交更新
        # ----------------------------------------------------
        await db.commit()

        # ----------------------------------------------------
        # 刷新数据库最新状态
        # ----------------------------------------------------
        await db.refresh(
            paper
        )

        logger.info(
            "Paper updated: id=%s owner_id=%s",
            paper.id,
            paper.owner_id,
        )

        return paper

    # ========================================================
    # DOI UNIQUE 冲突等数据库完整性异常
    # ========================================================

    except IntegrityError as exc:
        await db.rollback()

        if "uq_papers_doi" in str(exc.orig):
            logger.warning(
                "Duplicate DOI while updating paper: id=%s",
                paper.id,
            )

            raise PaperDOIExistsException() from exc

        logger.exception(
            "Integrity error while updating paper: id=%s",
            paper.id,
        )

        raise

    # ========================================================
    # 未知异常
    # ========================================================

    except Exception:
        await db.rollback()

        logger.exception(
            "Unexpected error while updating paper: id=%s",
            paper.id,
        )

        raise


# ============================================================
# 删除 Paper
# ============================================================

async def delete_paper(
    db: AsyncSession,
    paper: Paper,
) -> None:
    """
    删除 Paper。

    注意：

    进入这个函数之前，
    Router 已经调用 get_paper_by_id()
    完成：

        paper_id
        +
        owner_id

    权限检查。

    因此这里拿到的是当前用户自己的 Paper。
    """

    # ========================================================
    # 删除之前保存日志字段
    # ========================================================
    #
    # ORM 对象被 delete 后状态会变化，
    # 所以提前保存。
    #
    paper_id = paper.id
    owner_id = paper.owner_id

    try:
        # ----------------------------------------------------
        # 标记 ORM 对象为删除
        # ----------------------------------------------------
        await db.delete(
            paper
        )

        # ----------------------------------------------------
        # 提交 DELETE
        # ----------------------------------------------------
        await db.commit()

        logger.info(
            "Paper deleted: id=%s owner_id=%s",
            paper_id,
            owner_id,
        )

    except Exception:
        await db.rollback()

        logger.exception(
            "Unexpected error while deleting paper: "
            "id=%s owner_id=%s",
            paper_id,
            owner_id,
        )

        raise