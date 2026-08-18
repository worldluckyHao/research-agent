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


# ============================================================
# 当前 Service 模块 logger
# ============================================================
#
# 日志名称会类似：
#
# backend.app.services.paper_service
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

        # Day13：当前登录用户成为 owner。
        owner_id=owner_id,
    )

    try:
        db.add(paper)

        await db.commit()
        await db.refresh(paper)

        logger.info(
            "Paper created: id=%s owner_id=%s",
            paper.id,
            owner_id,
        )

        return paper

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

    except Exception:
        await db.rollback()

        logger.exception(
            "Unexpected error while creating paper"
        )

        raise


# ============================================================
# Paper 列表
# ============================================================

async def get_papers(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    year: Optional[int] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
):
    """
    查询 Paper 列表。

    支持：

    1. Pagination
    2. Filter
    3. Search
    4. Sorting
    """

    # ========================================================
    # 动态过滤条件
    # ========================================================

    filters = []

    # year 过滤：
    #
    # WHERE year = xxx
    if year is not None:
        filters.append(
            Paper.year == year
        )

    # source 过滤：
    #
    # WHERE source = xxx
    if source is not None:
        filters.append(
            Paper.source == source
        )

    # ========================================================
    # title + abstract 模糊搜索
    # ========================================================

    if search:
        # 例如：
        #
        # search = transformer
        #
        # 变成：
        #
        # %transformer%
        search_pattern = f"%{search}%"

        filters.append(
            or_(
                # title ILIKE '%xxx%'
                Paper.title.ilike(
                    search_pattern
                ),

                # abstract ILIKE '%xxx%'
                Paper.abstract.ilike(
                    search_pattern
                ),
            )
        )

    # ========================================================
    # 查询符合条件的总数量
    # ========================================================
    #
    # 注意：
    #
    # COUNT 必须使用和正式查询一样的 filters。
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

    # COUNT 只返回一个数，
    # 所以使用 scalar_one()。
    total = total_result.scalar_one()

    # ========================================================
    # 计算总页数
    # ========================================================

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
    # page=1:
    #
    # offset = 0
    #
    # page=2:
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
    # 不允许客户端直接随便控制 ORM 属性。
    #
    sort_columns = {
        "id": Paper.id,
        "title": Paper.title,
        "year": Paper.year,
        "created_at": Paper.created_at,
        "updated_at": Paper.updated_at,
    }

    # 如果出现未知 sort_by，
    # Service 层最后兜底使用 id。
    #
    # 正常情况下 Router 的 Literal 已经会提前拦截。
    sort_column = sort_columns.get(
        sort_by,
        Paper.id,
    )

    # ========================================================
    # ASC / DESC
    # ========================================================

    if sort_order == "desc":
        ordering = desc(sort_column)
    else:
        ordering = asc(sort_column)

    # ========================================================
    # 构造最终查询
    # ========================================================

    stmt = (
        select(Paper)

        # WHERE
        .where(*filters)

        # ORDER BY
        .order_by(ordering)

        # OFFSET
        .offset(offset)

        # LIMIT
        .limit(page_size)
    )

    # ========================================================
    # 执行 SQL
    # ========================================================

    result = await db.execute(stmt)

    # 提取 Paper ORM 对象。
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
) -> Optional[Paper]:
    """
    查询指定 Paper ID。

    找到：
        return Paper

    没找到：
        return None
    """

    result = await db.execute(
        select(Paper).where(
            Paper.id == paper_id
        )
    )

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

    只更新客户端真正提交的字段。
    """

    # ========================================================
    # exclude_unset=True
    # ========================================================
    #
    # 例如客户端只传：
    #
    # {
    #     "year": 2025
    # }
    #
    # 那么 update_data 就只有：
    #
    # {
    #     "year": 2025
    # }
    #
    update_data = paper_data.model_dump(
        exclude_unset=True
    )

    try:
        # ====================================================
        # 动态更新 ORM 属性
        # ====================================================
        #
        # 例如：
        #
        # field = "year"
        # value = 2025
        #
        # 相当于：
        #
        # paper.year = 2025
        #
        for field, value in update_data.items():
            setattr(
                paper,
                field,
                value,
            )

        # 提交数据库更新。
        await db.commit()

        # 重新获取最新数据库状态。
        await db.refresh(paper)

        logger.info(
            "Paper updated: id=%s",
            paper.id,
        )

        return paper

    # ========================================================
    # DOI UNIQUE 冲突等完整性异常
    # ========================================================

    except IntegrityError as exc:
        await db.rollback()

        # 如果违反的是 DOI 唯一约束：
        if "uq_papers_doi" in str(exc.orig):
            logger.warning(
                "Duplicate DOI while updating paper: id=%s",
                paper.id,
            )

            raise PaperDOIExistsException() from exc

        # 其他数据库完整性问题。
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

    流程：

    db.delete()
        ↓
    commit()

    如果失败：

    rollback()
    """

    # 先保存 ID。
    #
    # 因为删除以后 ORM 对象状态会发生变化，
    # 日志最好提前保存需要的信息。
    paper_id = paper.id

    try:
        # 标记 ORM 对象为删除状态。
        await db.delete(paper)

        # 真正提交 DELETE。
        await db.commit()

        logger.info(
            "Paper deleted: id=%s",
            paper_id,
        )

    except Exception:
        await db.rollback()

        logger.exception(
            "Unexpected error while deleting paper: id=%s",
            paper_id,
        )

        raise