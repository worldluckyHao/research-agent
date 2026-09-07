import logging
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    PaperImportJobNotFoundException,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.paper import Paper
from backend.app.models.paper_import_job import (
    PaperImportJob,
)
from backend.app.models.project_paper import ProjectPaper
from backend.app.schemas.external import (
    PaperImportRequest,
    UnifiedPaperMetadata,
)
from backend.app.services import (
    research_project,
)
from backend.app.services.paper_deduplication import (
    are_same_paper,
    merge_papers,
    normalize_arxiv_id,
    normalize_doi,
)


logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _paper_to_unified_metadata(
    paper: Paper,
) -> UnifiedPaperMetadata:
    """
    将数据库 Paper 转回统一 Metadata。

    这样我们可以复用 Day19：
    are_same_paper()
    merge_papers()
    """

    return UnifiedPaperMetadata(
        provider=(
            paper.source
            or "database"
        ),

        provider_id=str(
            paper.id
        ),

        sources=(
            paper.sources
            or []
        ),

        provider_ids=(
            paper.external_ids
            or {}
        ),

        title=paper.title,

        authors=(
            paper.authors
            or []
        ),

        abstract=paper.abstract,

        year=paper.year,

        doi=paper.doi,

        arxiv_id=paper.arxiv_id,

        url=paper.url,

        pdf_url=paper.pdf_url,

        venue=paper.venue,

        cited_by_count=(
            paper.cited_by_count
            or 0
        ),

        is_open_access=(
            paper.is_open_access
        ),

        language=paper.language,

        topics=(
            paper.keywords
            or []
        ),
    )


def _apply_metadata_to_paper(
    paper: Paper,
    metadata: UnifiedPaperMetadata,
) -> None:
    """
    将 Canonical Metadata 写回 Paper ORM。

    这个函数不 commit，
    Transaction 由调用方负责。
    """

    paper.title = metadata.title

    paper.authors = metadata.authors

    if metadata.year is not None:
        paper.year = metadata.year

    paper.doi = normalize_doi(
        metadata.doi
    )

    paper.arxiv_id = normalize_arxiv_id(
        metadata.arxiv_id
    )

    paper.url = metadata.url

    paper.pdf_url = metadata.pdf_url

    paper.source = metadata.provider

    paper.sources = (
        metadata.sources
        or [metadata.provider]
    )

    paper.external_ids = (
        metadata.provider_ids
        or {}
    )

    paper.abstract = metadata.abstract

    paper.keywords = metadata.topics

    paper.language = (
        metadata.language
        or paper.language
        or "en"
    )

    paper.venue = metadata.venue

    paper.cited_by_count = (
        metadata.cited_by_count
    )

    paper.is_open_access = (
        metadata.is_open_access
    )


# ============================================================
# Existing Paper Detection
# ============================================================

async def _find_existing_paper(
    db: AsyncSession,
    metadata: UnifiedPaperMetadata,
) -> Optional[Paper]:
    """
    查找数据库中是否已经存在同一篇 Paper。

    匹配优先级：

    1. DOI
    2. arXiv ID
    3. Title + Authors + Year
    """

    doi = normalize_doi(
        metadata.doi
    )


    # --------------------------------------------------------
    # Tier 1：DOI
    # --------------------------------------------------------

    if doi:
        result = await db.execute(
            select(Paper).where(
                func.lower(
                    Paper.doi
                ) == doi
            )
        )

        paper = result.scalar_one_or_none()

        if paper is not None:
            return paper


    arxiv_id = normalize_arxiv_id(
        metadata.arxiv_id
    )


    # --------------------------------------------------------
    # Tier 2：arXiv ID
    # --------------------------------------------------------

    if arxiv_id:
        result = await db.execute(
            select(Paper).where(
                func.lower(
                    Paper.arxiv_id
                ) == arxiv_id
            )
        )

        paper = result.scalar_one_or_none()

        if paper is not None:
            return paper


    # --------------------------------------------------------
    # Tier 3：Metadata Candidate Blocking
    # --------------------------------------------------------

    stmt = select(Paper)


    if metadata.year is not None:
        stmt = stmt.where(
            Paper.year.between(
                metadata.year - 1,
                metadata.year + 1,
            )
        )


    # 防止 fallback 在整个 papers 表做 O(n) 扫描。
    stmt = stmt.limit(100)


    result = await db.execute(
        stmt
    )


    candidates = (
        result.scalars().all()
    )


    for candidate in candidates:

        existing_metadata = (
            _paper_to_unified_metadata(
                candidate
            )
        )


        if are_same_paper(
            existing_metadata,
            metadata,
        ):
            return candidate


    return None


# ============================================================
# Idempotent Persistence
# ============================================================

async def import_paper_metadata(
    db: AsyncSession,
    metadata: UnifiedPaperMetadata,
    owner_id: int,
) -> tuple[Paper, bool]:
    """
    幂等导入 Canonical Paper。

    Returns:
        (paper, created)

    created=True:
        创建了新 Paper。

    created=False:
        找到已有 Paper，并完成 Metadata Merge。
    """

    existing = await _find_existing_paper(
        db=db,
        metadata=metadata,
    )


    # --------------------------------------------------------
    # Existing Paper -> Metadata Merge
    # --------------------------------------------------------

    if existing is not None:

        existing_metadata = (
            _paper_to_unified_metadata(
                existing
            )
        )


        merged_metadata = merge_papers(
            existing_metadata,
            metadata,
        )


        _apply_metadata_to_paper(
            existing,
            merged_metadata,
        )


        try:
            await db.commit()
            await db.refresh(
                existing
            )

            logger.info(
                "Paper import merged with existing: "
                "paper_id=%s",
                existing.id,
            )

            return (
                existing,
                False,
            )

        except Exception:
            await db.rollback()
            raise


    # --------------------------------------------------------
    # New Paper
    # --------------------------------------------------------

    # 数据库 year 当前为 NOT NULL。
    # 如果外部数据没有年份，
    # 当前阶段不直接导入不完整 Paper。
    if metadata.year is None:
        raise ValueError(
            "Paper year is required for import"
        )


    paper = Paper(
        title=metadata.title,

        authors=metadata.authors,

        year=metadata.year,

        doi=normalize_doi(
            metadata.doi
        ),

        arxiv_id=normalize_arxiv_id(
            metadata.arxiv_id
        ),

        url=metadata.url,

        pdf_url=metadata.pdf_url,

        source=metadata.provider,

        sources=(
            metadata.sources
            or [metadata.provider]
        ),

        external_ids=(
            metadata.provider_ids
            or {}
        ),

        abstract=metadata.abstract,

        keywords=metadata.topics,

        language=(
            metadata.language
            or "en"
        ),

        venue=metadata.venue,

        cited_by_count=(
            metadata.cited_by_count
        ),

        is_open_access=(
            metadata.is_open_access
        ),

        # 谁执行导入，
        # 谁成为这条本地 Paper 的 owner。
        owner_id=owner_id,
    )


    try:
        db.add(
            paper
        )

        await db.commit()

        await db.refresh(
            paper
        )

        logger.info(
            "Paper imported: "
            "paper_id=%s owner_id=%s",
            paper.id,
            owner_id,
        )

        return (
            paper,
            True,
        )


    # --------------------------------------------------------
    # Race Condition Protection
    # --------------------------------------------------------

    except IntegrityError as exc:

        await db.rollback()


        # 可能两个 Request 同时检查：
        #
        # A: 不存在
        # B: 不存在
        #
        # A INSERT 成功
        # B INSERT 命中 UNIQUE
        #
        # 此时重新查询即可。
        existing = await _find_existing_paper(
            db=db,
            metadata=metadata,
        )


        if existing is None:
            raise exc


        existing_metadata = (
            _paper_to_unified_metadata(
                existing
            )
        )


        merged_metadata = merge_papers(
            existing_metadata,
            metadata,
        )


        _apply_metadata_to_paper(
            existing,
            merged_metadata,
        )


        await db.commit()

        await db.refresh(
            existing
        )


        return (
            existing,
            False,
        )


# ============================================================
# Project Association
# ============================================================

async def _ensure_project_paper_link(
    db: AsyncSession,
    project_id: int,
    paper_id: int,
    user_id: int,
) -> None:
    """
    确保 Paper 属于指定 Project。

    该操作本身也是幂等的。
    """

    # Background Task 执行时再次做 owner check，
    # 防止任务排队期间 Project 状态发生变化。
    await research_project.get_owned_project(
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


    existing_link = (
        result.scalar_one_or_none()
    )


    if existing_link is not None:
        return


    link = ProjectPaper(
        project_id=project_id,
        paper_id=paper_id,
    )


    try:
        db.add(
            link
        )

        await db.commit()


    except IntegrityError:
        # 并发情况下复合 PK 会作为最终防线。
        await db.rollback()


        result = await db.execute(
            select(ProjectPaper).where(
                ProjectPaper.project_id == project_id,
                ProjectPaper.paper_id == paper_id,
            )
        )


        if result.scalar_one_or_none() is None:
            raise


# ============================================================
# Import Job CRUD
# ============================================================

async def create_import_job(
    db: AsyncSession,
    user_id: int,
    request_data: PaperImportRequest,
) -> PaperImportJob:
    """
    先持久化 Job，再启动 BackgroundTask。
    """

    job = PaperImportJob(
        id=str(
            uuid4()
        ),

        user_id=user_id,

        project_id=(
            request_data.project_id
        ),

        status="pending",

        # mode="json" 可确保 datetime/date
        # 被转换成 JSON 可存储格式。
        paper_payload=(
            request_data.paper.model_dump(
                mode="json"
            )
        ),
    )


    try:
        db.add(
            job
        )

        await db.commit()

        await db.refresh(
            job
        )


        logger.info(
            "Paper import job created: "
            "job_id=%s user_id=%s",
            job.id,
            user_id,
        )


        return job


    except Exception:
        await db.rollback()
        raise


async def get_import_job(
    db: AsyncSession,
    job_id: str,
    user_id: int,
) -> PaperImportJob:
    """
    只允许用户查看自己的 Job。
    """

    result = await db.execute(
        select(PaperImportJob).where(
            PaperImportJob.id == job_id,
            PaperImportJob.user_id == user_id,
        )
    )


    job = result.scalar_one_or_none()


    if job is None:
        raise PaperImportJobNotFoundException()


    return job


# ============================================================
# Background Worker
# ============================================================

async def run_paper_import_job(
    job_id: str,
) -> None:
    """
    FastAPI BackgroundTasks 调用入口。

    非常重要：
    这里不能复用 Request 中的 AsyncSession。

    因为 HTTP Response 返回后，
    request-scoped Session 已经结束。

    BackgroundTask 必须自己创建新的 Session。
    """

    async with AsyncSessionLocal() as db:

        # ----------------------------------------------------
        # Load Job
        # ----------------------------------------------------

        result = await db.execute(
            select(PaperImportJob).where(
                PaperImportJob.id == job_id
            )
        )


        job = result.scalar_one_or_none()


        if job is None:
            logger.error(
                "Import job disappeared: job_id=%s",
                job_id,
            )

            return


        try:
            # ------------------------------------------------
            # pending -> running
            # ------------------------------------------------

            job.status = "running"

            job.error_message = None

            await db.commit()


            metadata = (
                UnifiedPaperMetadata.model_validate(
                    job.paper_payload
                )
            )


            # ------------------------------------------------
            # Import / Merge
            # ------------------------------------------------

            paper, created = (
                await import_paper_metadata(
                    db=db,
                    metadata=metadata,
                    owner_id=job.user_id,
                )
            )


            # ------------------------------------------------
            # Optional Project Association
            # ------------------------------------------------

            if job.project_id is not None:

                await _ensure_project_paper_link(
                    db=db,
                    project_id=job.project_id,
                    paper_id=paper.id,
                    user_id=job.user_id,
                )


            # ------------------------------------------------
            # succeeded
            # ------------------------------------------------

            # import_paper_metadata() 内部 commit 过，
            # 但 AsyncSessionLocal expire_on_commit=False，
            # 当前 job 仍可以继续使用。
            job.status = "succeeded"

            job.paper_id = paper.id

            job.error_message = None


            await db.commit()


            logger.info(
                "Paper import job succeeded: "
                "job_id=%s paper_id=%s created=%s",
                job_id,
                paper.id,
                created,
            )

        except Exception:

            # 当前 Transaction 如果失败，先回滚。
            await db.rollback()


            logger.exception(
                "Paper import job failed: "
                "job_id=%s",
                job_id,
            )


            # 重新查询 Job，
            # 防止 rollback 后 ORM 状态不可靠。
            result = await db.execute(
                select(PaperImportJob).where(
                    PaperImportJob.id == job_id
                )
            )


            failed_job = (
                result.scalar_one_or_none()
            )


            if failed_job is not None:

                failed_job.status = "failed"

                failed_job.error_message = (
                    "Paper import failed"
                )


                await db.commit()


            # Day22：
            # 重新抛出异常，
            # 让 Celery 能感知任务失败，
            # 并根据异常类型决定是否 Retry。
            raise

class PaperImportService:
    """
    负责将外部论文元数据导入系统。
    """

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session

    async def import_paper(
        self,
        request: PaperImportRequest,
    ):
        """
        执行论文导入流程。

        当前阶段：
        1. 接收统一论文元数据
        2. 后续执行论文查重
        3. 创建或复用 Paper
        4. 可选关联 Research Project
        """

        paper_data: UnifiedPaperMetadata = request.paper

        # Day21 后续实现数据库导入逻辑
        return paper_data