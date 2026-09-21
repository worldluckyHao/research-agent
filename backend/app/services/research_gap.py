from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.agents.research_gap import (
    ResearchGapAgent,
)
from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    PaperComparisonLimitException,
    ResearchGapEvidenceUnavailableException,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.schemas.paper_comparison import (
    PaperComparisonRequest,
)
from backend.app.schemas.research_gap import (
    ResearchGapRequest,
    ResearchGapResponse,
)
from backend.app.services import (
    paper_comparison,
)


# ============================================================
# Public Service
# ============================================================

async def discover_project_research_gaps(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    request: ResearchGapRequest,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
) -> ResearchGapResponse:
    """
    Day39 Research Gap Service。

    Flow：

        Request
           ↓
        Day38 Comparison
           ↓
        Evidence Availability Check
           ↓
        Gap Generator
           ↓
        Gap Verifier
           ↓
        Response
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
    # 2. Gap Candidate Count Guard
    # ========================================================

    max_candidates = min(
        request.max_candidates,

        settings
        .RESEARCH_GAP_MAX_CANDIDATES,
    )


    # ========================================================
    # 3. Reuse Day38 Comparison
    # ========================================================

    comparison_request = (
        PaperComparisonRequest(
            items=(
                request.items
            ),

            focus=(
                request.comparison_focus
            ),

            response_language=(
                request.response_language
            ),
        )
    )


    comparison = (
        await paper_comparison
        .compare_project_papers(
            db=db,

            project_id=(
                project_id
            ),

            user_id=(
                user_id
            ),

            request=(
                comparison_request
            ),

            embedding_provider=(
                embedding_provider
            ),

            llm_provider=(
                llm_provider
            ),
        )
    )


    # ========================================================
    # 4. Cross-Paper Evidence Check
    # ========================================================

    papers_with_evidence = {
        paper.paper_id

        for paper
        in comparison.papers

        if paper.citations
    }


    # Research Gap 是 Cross-Paper Analysis。
    #
    # 如果只有一篇论文拥有可用 Evidence，
    # 就不应该假装完成了跨论文 Gap Discovery。
    if len(
        papers_with_evidence
    ) < 2:

        raise (
            ResearchGapEvidenceUnavailableException()
        )


    # ========================================================
    # 5. Normalize Gap Focus
    # ========================================================

    gap_focus = (
        request.gap_focus.strip()

        if request.gap_focus

        else (
            "Identify carefully scoped research gaps "
            "across methods, data, modalities, "
            "evaluation, robustness, generalization, "
            "interpretability, efficiency, and "
            "reproducibility."
        )
    )


    # ========================================================
    # 6. Agent
    # ========================================================

    agent = (
        ResearchGapAgent(
            llm_provider=(
                llm_provider
            )
        )
    )


    # ========================================================
    # 7. Discover
    # ========================================================

    return (
        await agent.discover(
            project_id=(
                project_id
            ),

            comparison=(
                comparison
            ),

            gap_focus=(
                gap_focus
            ),

            max_candidates=(
                max_candidates
            ),

            response_language=(
                request
                .response_language
            ),
        )
    )