from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.agents.research_experiment import (
    ResearchExperimentAgent,
)
from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    ResearchExperimentIdeaNotFoundException,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.schemas.research_experiment import (
    ResearchExperimentRequest,
    ResearchExperimentResponse,
)
from backend.app.schemas.research_idea import (
    ResearchIdeaRequest,
    ResearchIdeaResponse,
    ResearchIdeaResult,
)
from backend.app.services import (
    research_idea,
)


# ============================================================
# Idea Selection
# ============================================================

def _select_idea(
    research_idea_response: ResearchIdeaResponse,
    selected_idea_id: str | None,
) -> ResearchIdeaResult:
    """
    选择 Day41 要设计实验的 Idea。

    Explicit Selection：
        精确选择。

    Automatic Selection：
        1. recommended_for_experiment
        2. needs_revision
    """

    ideas = (
        research_idea_response.ideas
    )


    if not ideas:

        raise (
            ResearchExperimentIdeaNotFoundException()
        )


    # ========================================================
    # Explicit Selection
    # ========================================================

    if selected_idea_id:

        normalized_id = (
            selected_idea_id.strip()
        )


        for idea in ideas:

            if (
                idea.idea_id
                == normalized_id
            ):

                return idea


        raise (
            ResearchExperimentIdeaNotFoundException()
        )


    # ========================================================
    # Prefer Experiment-Ready Candidate
    # ========================================================

    for idea in ideas:

        if (
            idea.decision
            == "recommended_for_experiment"
        ):

            return idea


    # ========================================================
    # Fallback:
    # Needs Revision
    # ========================================================

    for idea in ideas:

        if (
            idea.decision
            == "needs_revision"
        ):

            return idea


    raise (
        ResearchExperimentIdeaNotFoundException()
    )


# ============================================================
# Public Service
# ============================================================

async def design_project_research_experiment(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    request: ResearchExperimentRequest,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
) -> ResearchExperimentResponse:
    """
    Day41 Experiment Design Service。

    Flow：

        Day40 Research Idea
            ↓
        Select Idea
            ↓
        Experiment Designer
            ↓
        Experiment Critic
    """

    # ========================================================
    # 1. Reuse Day40
    # ========================================================

    idea_request = (
        ResearchIdeaRequest(
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

            selected_gap_id=(
                request
                .selected_gap_id
            ),

            constraints=(
                request
                .constraints
            ),

            # Day41 需要有足够 Candidate
            # 才能按 idea_id 选择。
            max_ideas=(
                settings
                .RESEARCH_IDEA_MAX_CANDIDATES
            ),

            response_language=(
                request
                .response_language
            ),
        )
    )


    research_idea_response = (
        await research_idea
        .generate_project_research_ideas(
            db=db,

            project_id=(
                project_id
            ),

            user_id=(
                user_id
            ),

            request=(
                idea_request
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
    # 2. Select Idea
    # ========================================================

    selected_idea = (
        _select_idea(
            research_idea_response=(
                research_idea_response
            ),

            selected_idea_id=(
                request
                .selected_idea_id
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
            "Use reproducible experimental settings, "
            "prefer publicly available data, keep "
            "baseline comparisons fair, avoid test-set "
            "tuning, and design experiments that can be "
            "executed within a graduate research project."
        )
    )


    # ========================================================
    # 4. Normalize Experiment Focus
    # ========================================================

    experiment_focus = (
        request.experiment_focus.strip()

        if request.experiment_focus

        else (
            "Design rigorous main experiments, baseline "
            "comparisons, ablations, hyperparameter "
            "studies, statistical analysis, leakage "
            "controls, and reproducibility checks."
        )
    )


    # ========================================================
    # 5. Agent
    # ========================================================

    agent = (
        ResearchExperimentAgent(
            llm_provider=(
                llm_provider
            )
        )
    )


    # ========================================================
    # 6. Experiment Design
    # ========================================================

    return (
        await agent.design_experiment(
            project_id=(
                project_id
            ),

            research_idea=(
                research_idea_response
            ),

            selected_idea=(
                selected_idea
            ),

            constraints=(
                constraints
            ),

            experiment_focus=(
                experiment_focus
            ),

            response_language=(
                request
                .response_language
            ),
        )
    )