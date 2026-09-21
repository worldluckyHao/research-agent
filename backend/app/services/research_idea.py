from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.agents.research_idea import (
    ResearchIdeaAgent,
)
from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    ResearchIdeaGapNotFoundException,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.schemas.research_gap import (
    ResearchGapRequest,
)
from backend.app.schemas.research_idea import (
    ResearchIdeaRequest,
    ResearchIdeaResponse,
)
from backend.app.services import (
    research_gap,
)


# ============================================================
# Gap Selection
# ============================================================

def _select_gap(
    research_gap_response,
    selected_gap_id,
):
    """
    选择 Day40 使用的 Verified Gap。

    如果指定 selected_gap_id：
        精确选择。

    否则：
        优先选择第一个 supported，
        再选择 partially_supported。
    """

    gaps = (
        research_gap_response.gaps
    )


    if not gaps:

        raise (
            ResearchIdeaGapNotFoundException()
        )


    # ========================================================
    # Explicit Selection
    # ========================================================

    if selected_gap_id:

        normalized_id = (
            selected_gap_id
            .strip()
        )


        for gap in gaps:

            if (
                gap.gap_id
                == normalized_id
            ):

                return gap


        raise (
            ResearchIdeaGapNotFoundException()
        )


    # ========================================================
    # Prefer Supported
    # ========================================================

    for gap in gaps:

        if (
            gap.verification_status
            == "supported"
        ):

            return gap


    # ========================================================
    # Fallback Partial
    # ========================================================

    for gap in gaps:

        if (
            gap.verification_status
            == "partially_supported"
        ):

            return gap


    raise (
        ResearchIdeaGapNotFoundException()
    )


# ============================================================
# Public Service
# ============================================================

async def generate_project_research_ideas(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    request: ResearchIdeaRequest,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
) -> ResearchIdeaResponse:
    """
    Day40 Research Idea Service。

    Flow:

        Day39 Research Gap
            ↓
        Select Verified Gap
            ↓
        Idea Generator
            ↓
        Feasibility Critic
            ↓
        Novelty-Risk Critic
            ↓
        Implementation Planner
    """

    # ========================================================
    # 1. Reuse Day39
    # ========================================================

    gap_request = (
        ResearchGapRequest(
            items=(
                request.items
            ),

            comparison_focus=(
                request
                .comparison_focus
            ),

            gap_focus=(
                request
                .gap_focus
            ),

            max_candidates=(
                settings
                .RESEARCH_GAP_MAX_CANDIDATES
            ),

            response_language=(
                request
                .response_language
            ),
        )
    )


    research_gap_response = (
        await research_gap
        .discover_project_research_gaps(
            db=db,

            project_id=(
                project_id
            ),

            user_id=(
                user_id
            ),

            request=(
                gap_request
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
    # 2. Select Gap
    # ========================================================

    selected_gap = (
        _select_gap(
            research_gap_response=(
                research_gap_response
            ),

            selected_gap_id=(
                request
                .selected_gap_id
            ),
        )
    )


    # ========================================================
    # 3. Normalize Constraints
    # ========================================================

    constraints = (
        request.constraints.strip()

        if request.constraints

        else (
            "Prefer publicly available datasets, "
            "reproducible experiments, and a scope "
            "that can be implemented in a graduate "
            "research project."
        )
    )


    # ========================================================
    # 4. Candidate Count Guard
    # ========================================================

    max_ideas = min(
        request.max_ideas,

        settings
        .RESEARCH_IDEA_MAX_CANDIDATES,
    )


    # ========================================================
    # 5. Agent
    # ========================================================

    agent = (
        ResearchIdeaAgent(
            llm_provider=(
                llm_provider
            )
        )
    )


    # ========================================================
    # 6. Generate
    # ========================================================

    return (
        await agent.generate_ideas(
            project_id=(
                project_id
            ),

            research_gap=(
                research_gap_response
            ),

            selected_gap=(
                selected_gap
            ),

            constraints=(
                constraints
            ),

            max_ideas=(
                max_ideas
            ),

            response_language=(
                request
                .response_language
            ),
        )
    )