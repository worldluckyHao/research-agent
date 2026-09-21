from sqlalchemy import (
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.agents.paper_comparison import (
    ComparisonPaperSource,
    PaperComparisonAgent,
)
from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    PaperComparisonLimitException,
    PaperComparisonProjectNotFoundException,
    PaperComparisonSourceNotFoundException,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.models.paper import (
    Paper,
)
from backend.app.models.paper_document import (
    PaperDocument,
)
from backend.app.models.project_paper import (
    ProjectPaper,
)
from backend.app.models.research_project import (
    ResearchProject,
)
from backend.app.schemas.paper_comparison import (
    PaperComparisonRequest,
    PaperComparisonResponse,
)


# ============================================================
# Project Authorization
# ============================================================

async def _get_owned_project(
    db: AsyncSession,
    project_id: int,
    user_id: int,
) -> ResearchProject:
    """
    验证当前 ResearchProject
    属于当前 User。

    不区分：
        项目不存在
        项目属于别人

    统一 404，
    减少 Resource Enumeration。
    """

    result = await db.execute(
        select(
            ResearchProject
        ).where(
            ResearchProject.id
            == project_id,

            ResearchProject.owner_id
            == user_id,
        )
    )


    project = (
        result.scalar_one_or_none()
    )


    if project is None:

        raise (
            PaperComparisonProjectNotFoundException()
        )


    return project


# ============================================================
# Paper Membership
# ============================================================

async def _validate_project_paper(
    db: AsyncSession,
    project_id: int,
    paper_id: int,
) -> None:
    """
    验证 Paper 确实属于这个 Project。
    """

    result = await db.execute(
        select(
            ProjectPaper
        ).where(
            ProjectPaper.project_id
            == project_id,

            ProjectPaper.paper_id
            == paper_id,
        )
    )


    project_paper = (
        result.scalar_one_or_none()
    )


    if project_paper is None:

        raise (
            PaperComparisonSourceNotFoundException()
        )


# ============================================================
# Paper + Document
# ============================================================

async def _load_comparison_source(
    db: AsyncSession,
    project_id: int,
    paper_id: int,
    document_id: int,
) -> ComparisonPaperSource:
    """
    加载并验证：

        Project
          ↓
        Paper
          ↓
        PaperDocument
    """

    # --------------------------------------------------------
    # 1. Paper must belong to Project
    # --------------------------------------------------------

    await _validate_project_paper(
        db=db,

        project_id=(
            project_id
        ),

        paper_id=(
            paper_id
        ),
    )


    # --------------------------------------------------------
    # 2. Paper
    # --------------------------------------------------------

    paper_result = await db.execute(
        select(
            Paper
        ).where(
            Paper.id
            == paper_id
        )
    )


    paper = (
        paper_result
        .scalar_one_or_none()
    )


    if paper is None:

        raise (
            PaperComparisonSourceNotFoundException()
        )


    # --------------------------------------------------------
    # 3. Document must belong to selected Paper
    # --------------------------------------------------------

    document_result = (
        await db.execute(
            select(
                PaperDocument
            ).where(
                PaperDocument.id
                == document_id,

                PaperDocument.paper_id
                == paper_id,
            )
        )
    )


    document = (
        document_result
        .scalar_one_or_none()
    )


    if document is None:

        raise (
            PaperComparisonSourceNotFoundException()
        )


    return ComparisonPaperSource(
        paper=(
            paper
        ),

        document=(
            document
        ),
    )


# ============================================================
# Public Service
# ============================================================

async def compare_project_papers(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    request: PaperComparisonRequest,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
) -> PaperComparisonResponse:
    """
    Day38 Paper Comparison Service。

    Responsibilities：

        1. Authorization
        2. Project Membership Validation
        3. Resource Loading
        4. Agent Invocation

    AI Logic：
        PaperComparisonAgent

    Authorization Logic：
        Service Layer
    """

    # ========================================================
    # 1. Paper Count Guard
    # ========================================================

    if (
        len(request.items)
        >
        settings
        .PAPER_COMPARISON_MAX_PAPERS
    ):

        raise (
            PaperComparisonLimitException(
                max_papers=(
                    settings
                    .PAPER_COMPARISON_MAX_PAPERS
                )
            )
        )


    # ========================================================
    # 2. Project Authorization
    # ========================================================

    await _get_owned_project(
        db=db,

        project_id=(
            project_id
        ),

        user_id=(
            user_id
        ),
    )


    # ========================================================
    # 3. Load Sources
    # ========================================================

    sources = []


    # 当前最多 5 篇，
    # 顺序查询足够清晰。
    #
    # 后续 Day55 性能优化时
    # 可以改成一次 Batch Query。
    for item in request.items:

        source = (
            await _load_comparison_source(
                db=db,

                project_id=(
                    project_id
                ),

                paper_id=(
                    item.paper_id
                ),

                document_id=(
                    item.document_id
                ),
            )
        )


        sources.append(
            source
        )


    # ========================================================
    # 4. Create Agent
    # ========================================================

    agent = (
        PaperComparisonAgent(
            llm_provider=(
                llm_provider
            )
        )
    )


    # ========================================================
    # 5. Compare
    # ========================================================

    return (
        await agent.compare(
            db=db,

            project_id=(
                project_id
            ),

            sources=(
                sources
            ),

            focus=(
                request.focus
            ),

            response_language=(
                request.response_language
            ),

            embedding_provider=(
                embedding_provider
            ),
        )
    )